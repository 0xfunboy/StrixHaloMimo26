#!/usr/bin/env python3
from __future__ import annotations
import json, os, signal, subprocess, time, urllib.request
from pathlib import Path

from perf_baseline_adapters import LlamaStreamCollector
from perf_baseline_common import atomic_json, meminfo, vmstat, proc_io, proc_status, hwmon, SANITY, CODE_PROMPT, code_gate

ROOT=Path("/home/funboy/StrixHaloMimo26")
RUN=Path(os.environ["MIMO26_PERF_RUN"])
WORKLOADS=json.loads((ROOT/"docs/mimo26/perf-baseline-001/workloads.json").read_text())
SERVER=os.environ["MIMO26_LLAMA_SERVER"]
MODEL=os.environ["MIMO26_GGUF_FIRST_SHARD"]
PORT=int(os.environ.get("MIMO26_PORT","18401"))
BASE=f"http://127.0.0.1:{PORT}"
LOG=RUN/"server.log"
RUN.mkdir(parents=True,exist_ok=True)

def req_json(path:str,payload=None,timeout=30):
    data=None if payload is None else json.dumps(payload).encode()
    r=urllib.request.Request(BASE+path,data=data,headers={"Content-Type":"application/json"},method="POST" if data is not None else "GET")
    with urllib.request.urlopen(r,timeout=timeout) as resp:
        raw=resp.read()
        return resp.status,json.loads(raw.decode()) if raw else None

def sanity(phase:str)->dict:
    tests=[]
    for name,prompt,check,max_tokens in SANITY:
        payload={"model":"mimo26-mixed","messages":[{"role":"user","content":prompt}],"temperature":0,"max_tokens":max_tokens,"stream":False}
        t=time.perf_counter()
        try:
            _,resp=req_json("/v1/chat/completions",payload,timeout=180)
            wall=time.perf_counter()-t
            c=resp["choices"][0]; m=c["message"]; txt=(m.get("content") or "").strip()
            try:ok=bool(check(txt)); reason="PASS" if ok else "expected_mismatch"
            except Exception as e:ok=False; reason=f"check:{type(e).__name__}:{e}"
            tests.append({"name":name,"pass":ok,"reason":reason,"text":txt,"finish_reason":c.get("finish_reason"),"wall_s":wall})
        except Exception as e:
            tests.append({"name":name,"pass":False,"reason":f"request:{type(e).__name__}:{e}","text":"","finish_reason":None})
    payload={"model":"mimo26-mixed","messages":[{"role":"user","content":CODE_PROMPT}],"temperature":0,"max_tokens":96,"stream":False}
    t=time.perf_counter()
    try:
        _,resp=req_json("/v1/chat/completions",payload,timeout=180)
        wall=time.perf_counter()-t; c=resp["choices"][0]; txt=(c["message"].get("content") or "").strip()
        ok,reason=code_gate(txt)
        tests.append({"name":"code_clamp","pass":ok,"reason":reason,"text":txt,"finish_reason":c.get("finish_reason"),"wall_s":wall})
    except Exception as e:
        tests.append({"name":"code_clamp","pass":False,"reason":f"request:{type(e).__name__}:{e}","text":"","finish_reason":None})
    out={"phase":phase,"status":"PASS" if all(x["pass"] for x in tests) else "FAIL","tests":tests}
    atomic_json(RUN/f"sanity-{phase}.json",out)
    return out

def stream_completion(ids:list[int],target:int,rep:int,warmup:bool)->dict:
    payload={
      "prompt":ids,"n_predict":128 if not warmup else 8,
      "temperature":0.0,"seed":1,"ignore_eos":True,
      "stream":True,"cache_prompt":False,"return_tokens":True,
      "return_progress":True,"timings_per_token":True,
    }
    before={"meminfo":meminfo(),"vmstat":vmstat(),"hwmon":hwmon(),"proc_io":proc_io(server.pid),"proc_status":proc_status(server.pid)}
    t_submit=time.perf_counter()
    collector=LlamaStreamCollector(t_submit)
    err=None
    try:
        data=json.dumps(payload).encode()
        request=urllib.request.Request(BASE+"/completion",data=data,headers={"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(request,timeout=600) as resp:
            for raw in resp:
                line=raw.decode(errors="replace").strip()
                if not line or line.startswith(":"):continue
                if line.startswith("data:"):line=line[5:].strip()
                if line=="[DONE]":continue
                try:event=json.loads(line)
                except Exception:continue
                collector.feed(time.perf_counter(),event)
    except Exception as e:
        err=f"{type(e).__name__}:{e}"
    t_done=time.perf_counter()
    after={"meminfo":meminfo(),"vmstat":vmstat(),"hwmon":hwmon(),"proc_io":proc_io(server.pid),"proc_status":proc_status(server.pid)}
    norm=collector.finish(t_done,error=err).normalized()
    final=norm.get("final_event") or {}
    timings=final.get("timings") or {}
    rec={
      "arm":"A","warmup":warmup,"input_tokens_target":target,"rep":rep,
      "input_token_ids_sha256":WORKLOADS["workloads"][str(target)]["input_token_ids_sha256"],
      "input_token_count":len(ids),"sampling":payload,
      "stream":norm,"native":{
        "timings":timings,
        "tokens_cached":final.get("tokens_cached"),
        "tokens_evaluated":final.get("tokens_evaluated"),
        "truncated":final.get("truncated"),
        "stop_type":final.get("stop_type"),
      },
      "system_before":before,"system_after":after,
    }
    rec["gates"]={
      "complete":bool(norm["complete"]),
      "output_128":True if warmup else norm["output_tokens"]==128,
      "cache_zero":(final.get("tokens_cached") in (0,None)) if warmup else final.get("tokens_cached")==0,
      "input_processed_exact":True if warmup else (
          timings.get("prompt_n")==target or final.get("tokens_evaluated")==target
      ),
    }
    return rec

server=None
def stop():
    global server
    if server is not None and server.poll() is None:
        server.terminate()
        try:server.wait(timeout=30)
        except subprocess.TimeoutExpired:server.kill();server.wait()
def sig(s,f):stop();raise SystemExit(128+s)
signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)

load_before=meminfo()
cmd=[SERVER,"-m",MODEL,"--device","ROCm0","--split-mode","none","-ngl","all","-c","4096","-b","512","-ub","128","-np","1","--no-cont-batching","-fa","auto","--host","127.0.0.1","--port",str(PORT),"--reasoning","off","--metrics"]
log=LOG.open("w")
start=time.perf_counter()
server=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
atomic_json(RUN/"load.json",{"status":"IN_PROGRESS","command":cmd,"memory_before":load_before})
deadline=time.monotonic()+900
while time.monotonic()<deadline:
    if server.poll() is not None:
        atomic_json(RUN/"load.json",{"status":"FAIL","exit_code":server.returncode});raise SystemExit(41)
    try:
        code,_=req_json("/health",timeout=2)
        if code==200:break
    except Exception:pass
    time.sleep(1)
else:
    stop();atomic_json(RUN/"load.json",{"status":"FAIL","cause":"READY_TIMEOUT"});raise SystemExit(42)

atomic_json(RUN/"load.json",{
  "status":"PASS","load_s":time.perf_counter()-start,"pid":server.pid,"command":cmd,
  "memory_before":load_before,"memory_after":meminfo(),"proc_status":proc_status(server.pid),
  "runtime_commit":"58367713a6935c0810103378144008df32e3d5db"
})
pre=sanity("pre")
if pre["status"]!="PASS":stop();raise SystemExit(43)

# Warmup: one request at each size, excluded.
warm=[]
for target in WORKLOADS["warmup_order"]:
    warm.append(stream_completion(WORKLOADS["workloads"][str(target)]["input_token_ids"],target,0,True))
atomic_json(RUN/"warmup.json",{"status":"COMPLETE","samples":warm})

rows=[]
counts={512:0,2048:0}
raw=RUN/"requests.jsonl"
for target in WORKLOADS["request_order"]:
    counts[target]+=1
    rec=stream_completion(WORKLOADS["workloads"][str(target)]["input_token_ids"],target,counts[target],False)
    rows.append(rec)
    with raw.open("a") as f:
        f.write(json.dumps(rec,ensure_ascii=False)+"\n");f.flush();os.fsync(f.fileno())
    atomic_json(RUN/"progress.json",{"completed":len(rows),"expected":6,"requests":rows})

post=sanity("post")
gates=[all(r["gates"].values()) for r in rows]
quality={"status":"PASS" if pre["status"]=="PASS" and post["status"]=="PASS" else "FAIL","pre":pre,"post":post}
atomic_json(RUN/"quality.json",quality)
result={"schema":"mimo26-perf-baseline-arm-a-v1","arm":"A","load":json.loads((RUN/"load.json").read_text()),"quality":quality,"warmup":warm,"requests":rows,"all_request_gates_pass":all(gates)}
atomic_json(RUN/"arm-result.json",result)
stop();log.close()
raise SystemExit(0 if quality["status"]=="PASS" and all(gates) else 44)
