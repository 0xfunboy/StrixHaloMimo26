#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, time
from pathlib import Path

import torch.distributed as dist
from vllm import LLM, SamplingParams

from perf_baseline_adapters import vllm_metrics
from perf_baseline_common import atomic_json, meminfo, vmstat, proc_io, proc_status, hwmon, netdev, SANITY, CODE_PROMPT, code_gate
from vllm_patch import apply_mimo26_vllm_patches

ROOT=Path("/home/funboy/StrixHaloMimo26")
RUN=Path(os.environ["MIMO26_PERF_RUN"])
WORKLOADS=json.loads((ROOT/"docs/mimo26/perf-baseline-001/workloads.json").read_text())
MODEL="/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL"
RANK=int(os.environ.get("RANK","0"))
RUN.mkdir(parents=True,exist_ok=True)

def remote_sample() -> dict:
    code=r'''
import json
from pathlib import Path
def meminfo():
 o={}
 for l in Path("/proc/meminfo").read_text().splitlines():
  if ":" in l:
   k,v=l.split(":",1); p=v.strip().split()
   if p and p[0].isdigit(): o[k]=int(p[0])*1024
 return o
def vmstat():
 o={}
 for l in Path("/proc/vmstat").read_text().splitlines():
  p=l.split()
  if len(p)==2 and p[1].isdigit() and p[0] in {"pgfault","pgmajfault","pswpin","pswpout"}:o[p[0]]=int(p[1])
 return o
def net():
 o={}; r=Path("/sys/class/net/thunderbolt0/statistics")
 for k in ("rx_bytes","tx_bytes","rx_packets","tx_packets","rx_errors","tx_errors"):
  try:o[k]=int((r/k).read_text())
  except:pass
 return o
def hw():
 for d in Path("/sys/class/hwmon").glob("hwmon*"):
  try:n=(d/"name").read_text().strip()
  except:continue
  if n=="amdgpu":
   o={"name":n}
   for f in ("temp1_input","freq1_input","power1_average","power1_input"):
    try:o[f]=int((d/f).read_text().strip())
    except:pass
   return o
 return {}
print(json.dumps({"meminfo":meminfo(),"vmstat":vmstat(),"netdev":net(),"hwmon":hw()}))
'''
    cp=subprocess.run(["ssh","-o","IdentityAgent=none","-o","BatchMode=yes","02-evo-x3-tb","python3 -c "+json.dumps(code)],capture_output=True,text=True)
    if cp.returncode: return {"error":cp.stderr.strip()}
    try:return json.loads(cp.stdout)
    except:return {"error":"bad_json","stdout":cp.stdout}

def local_sample() -> dict:
    return {"meminfo":meminfo(),"vmstat":vmstat(),"hwmon":hwmon(),"netdev":netdev(),"proc_io":proc_io(os.getpid()),"proc_status":proc_status(os.getpid())}

def chat_ids(tok,prompt:str)->list[int]:
    x=tok.apply_chat_template([{"role":"user","content":prompt}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
    if hasattr(x,"keys"):x=x["input_ids"]
    if hasattr(x,"tolist"):x=x.tolist()
    if x and isinstance(x[0],list):x=x[0]
    return [int(v) for v in x]

apply_mimo26_vllm_patches()
t0=time.perf_counter()
llm=LLM(
    model=MODEL,runner="generate",trust_remote_code=True,language_model_only=True,
    tensor_parallel_size=2,pipeline_parallel_size=1,distributed_executor_backend="external_launcher",
    dtype="bfloat16",max_model_len=4096,max_num_seqs=1,max_num_batched_tokens=512,
    gpu_memory_utilization=0.90,kv_cache_memory_bytes=1073741824,
    enforce_eager=True,disable_custom_all_reduce=True,enable_expert_parallel=False,
    enable_prefix_caching=False,seed=1,moe_backend="triton_unfused",
)
load_s=time.perf_counter()-t0
tok=llm.get_tokenizer()
if RANK==0:
    atomic_json(RUN/"load.json",{
      "status":"PASS","load_s":load_s,"rank":RANK,"memory_after":meminfo(),"proc_status":proc_status(os.getpid()),
      "tp":2,"pp":1,"kv_cache_memory_bytes":1073741824,"prefix_caching":False,
      "patch_source":"vllm-57508-backport-ckpt-tp4"
    })

def generate_ids(ids:list[int],n:int,ignore_eos:bool=True):
    p=SamplingParams(temperature=0.0,seed=1,max_tokens=n,min_tokens=n if ignore_eos else 0,ignore_eos=ignore_eos)
    t=time.perf_counter()
    out=llm.generate(ids,p,use_tqdm=False)[0]
    done=time.perf_counter()
    return out,t,done

def sanity(phase:str)->dict:
    tests=[]
    for name,prompt,check,max_tokens in SANITY:
        ids=chat_ids(tok,prompt)
        p=SamplingParams(temperature=0.0,seed=1,max_tokens=max_tokens,ignore_eos=False)
        t=time.perf_counter(); out=llm.generate(ids,p,use_tqdm=False)[0]; wall=time.perf_counter()-t
        c=out.outputs[0]; txt=c.text.strip()
        try:ok=bool(check(txt));reason="PASS" if ok else "expected_mismatch"
        except Exception as e:ok=False;reason=f"check:{type(e).__name__}:{e}"
        tests.append({"name":name,"pass":ok,"reason":reason,"text":txt,"finish_reason":c.finish_reason,"wall_s":wall})
    ids=chat_ids(tok,CODE_PROMPT)
    p=SamplingParams(temperature=0.0,seed=1,max_tokens=96,ignore_eos=False)
    t=time.perf_counter();out=llm.generate(ids,p,use_tqdm=False)[0];wall=time.perf_counter()-t
    c=out.outputs[0];ok,reason=code_gate(c.text.strip())
    tests.append({"name":"code_clamp","pass":ok,"reason":reason,"text":c.text.strip(),"finish_reason":c.finish_reason,"wall_s":wall})
    doc={"phase":phase,"status":"PASS" if all(x["pass"] for x in tests) else "FAIL","tests":tests}
    if RANK==0:atomic_json(RUN/f"sanity-{phase}.json",doc)
    return doc

pre=sanity("pre")
if pre["status"]!="PASS":
    if dist.is_initialized():dist.barrier()
    raise SystemExit(43)

warm=[]
for target in WORKLOADS["warmup_order"]:
    ids=WORKLOADS["workloads"][str(target)]["input_token_ids"]
    out,t,done=generate_ids(ids,8,True)
    if RANK==0:
        warm.append({"input_tokens":target,"output_tokens":len(out.outputs[0].token_ids),"wall_s":done-t})
if RANK==0:atomic_json(RUN/"warmup.json",{"status":"COMPLETE","samples":warm})

rows=[];counts={512:0,2048:0};raw=RUN/"requests.jsonl"
for target in WORKLOADS["request_order"]:
    counts[target]+=1
    ids=WORKLOADS["workloads"][str(target)]["input_token_ids"]
    if RANK==0:
        before={"node01":local_sample(),"node02":remote_sample()}
    out,t_submit,t_done=generate_ids(ids,128,True)
    if RANK==0:
        after={"node01":local_sample(),"node02":remote_sample()}
        rec=vllm_metrics(out,t_submit,t_done)
        rec.update({
          "arm":"B","input_tokens_target":target,"rep":counts[target],
          "input_token_ids_sha256":WORKLOADS["workloads"][str(target)]["input_token_ids_sha256"],
          "system_before":before,"system_after":after,
        })
        rec["gates"]={
          "output_128":rec["output_tokens"]==128,
          "input_ids_exact":rec["input_token_ids"]==ids,
          "cache_zero":rec["num_cached_tokens"] in (0,None),
        }
        rows.append(rec)
        with raw.open("a") as f:
            f.write(json.dumps(rec,ensure_ascii=False)+"\n");f.flush();os.fsync(f.fileno())
        atomic_json(RUN/"progress.json",{"completed":len(rows),"expected":6,"requests":rows})

post=sanity("post")
if RANK==0:
    quality={"status":"PASS" if pre["status"]=="PASS" and post["status"]=="PASS" else "FAIL","pre":pre,"post":post}
    atomic_json(RUN/"quality.json",quality)
    result={"schema":"mimo26-perf-baseline-arm-b-v1","arm":"B","load":json.loads((RUN/"load.json").read_text()),"quality":quality,"warmup":warm,"requests":rows,"all_request_gates_pass":all(all(r["gates"].values()) for r in rows)}
    atomic_json(RUN/"arm-result.json",result)
    rc=0 if quality["status"]=="PASS" and result["all_request_gates_pass"] else 44
else:
    rc=0
if dist.is_initialized():dist.barrier()
raise SystemExit(rc)
