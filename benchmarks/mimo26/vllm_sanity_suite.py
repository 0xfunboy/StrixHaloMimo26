#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import socket
import time
import unicodedata
from pathlib import Path

import torch.distributed as dist
from vllm import LLM, SamplingParams
from vllm_patch import apply_mimo26_vllm_patches

MODEL=os.environ.get("MIMO26_MODEL","/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL")
RUN=Path(os.environ["MIMO26_RUN_DIR"])
TP=int(os.environ.get("MIMO26_TP","2"))
KV_BYTES=int(os.environ.get("MIMO26_KV_BYTES","1073741824"))
MAX_LEN=int(os.environ.get("MIMO26_MAX_LEN","4096"))
MAX_BATCHED=int(os.environ.get("MIMO26_MAX_BATCHED","512"))
MOE=os.environ.get("MIMO26_MOE_BACKEND","triton_unfused")
rank=int(os.environ.get("RANK","0"))

def atomic(path:Path,obj):
    if rank!=0: return
    path.parent.mkdir(parents=True,exist_ok=True)
    q=path.with_suffix(path.suffix+".tmp")
    q.write_text(json.dumps(obj,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    os.replace(q,path)

def event(kind,**kw):
    if rank!=0: return
    rec={"ts":time.time(),"iso":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"event":kind,**kw}
    with (RUN/"events.jsonl").open("a") as f:
        f.write(json.dumps(rec,ensure_ascii=False,sort_keys=True)+"\n"); f.flush(); os.fsync(f.fileno())

def normalize_word(s:str)->str:
    s=s.strip().lower().rstrip(" .,!?:;")
    return unicodedata.normalize("NFC",s)

apply_mimo26_vllm_patches()
event("ENGINE_CREATE_START",hostname=socket.gethostname(),tp=TP)
t0=time.perf_counter()
llm=LLM(
    model=MODEL,
    runner="generate",
    trust_remote_code=True,
    language_model_only=True,
    tensor_parallel_size=TP,
    pipeline_parallel_size=1,
    distributed_executor_backend="external_launcher",
    dtype="bfloat16",
    max_model_len=MAX_LEN,
    max_num_seqs=1,
    max_num_batched_tokens=MAX_BATCHED,
    gpu_memory_utilization=0.90,
    kv_cache_memory_bytes=KV_BYTES,
    enforce_eager=True,
    disable_custom_all_reduce=True,
    enable_expert_parallel=False,
    enable_prefix_caching=False,
    moe_backend=MOE,
    seed=1,
)
load_s=time.perf_counter()-t0
load={
  "status":"PASS","load_s":load_s,"hostname":socket.gethostname(),
  "tp":TP,"kv_cache_memory_bytes":KV_BYTES,"max_model_len":MAX_LEN,
  "moe_backend":MOE,"patch_source":"vllm-57508-backport-ckpt-tp4",
}
atomic(RUN/"load.json",load)
event("LOAD_COMPLETE",load_s=load_s)

tok=llm.get_tokenizer()

def render_ids(text:str):
    msgs=[{"role":"user","content":text}]
    rendered=tok.apply_chat_template(
        msgs,tokenize=False,add_generation_prompt=True,enable_thinking=False
    )
    ids=tok.encode(rendered,add_special_tokens=False)
    if not ids or not all(isinstance(x,int) for x in ids):
        raise TypeError(f"prompt ids are not list[int]: {type(ids)}")
    return rendered,ids

def greedy(text:str,max_tokens:int=64):
    rendered,ids=render_ids(text)
    params=SamplingParams(temperature=0.0,seed=1,max_tokens=max_tokens,ignore_eos=False)
    event("SANITY_REQUEST_START",prompt_tokens=len(ids))
    t=time.perf_counter()
    out=llm.generate({"prompt_token_ids":ids},params,use_tqdm=False)[0]
    wall=time.perf_counter()-t
    c=out.outputs[0]
    return {
      "prompt":text,"rendered_prompt":rendered,"prompt_token_ids":ids,
      "output_token_ids":list(c.token_ids),"text":c.text,
      "finish_reason":c.finish_reason,"wall_s":wall,
    }

tests=[
  {
    "id":"arithmetic",
    "prompt":"Compute 17*19. Return only the integer, with no explanation.",
    "max_tokens":32,
  },
  {
    "id":"copy_exact",
    "prompt":"Return exactly this string and nothing else: ALPHA-7-zeta",
    "max_tokens":32,
  },
  {
    "id":"json_simple",
    "prompt":"Return exactly one JSON object and no other text. It must have key a with integer value 7 and key b with string value x.",
    "max_tokens":48,
  },
  {
    "id":"comprehension_it",
    "prompt":"Testo: Il laboratorio rosso apre martedì. Il laboratorio blu apre venerdì. In quale giorno apre il laboratorio rosso? Rispondi con una sola parola.",
    "max_tokens":32,
  },
]

partial={"schema":"mimo26-sanity-v1","status":"IN_PROGRESS","tests":[]}
atomic(RUN/"quality.partial.json",partial)
event("SANITY_SUITE_START",count=len(tests))

for spec in tests:
    rec=greedy(spec["prompt"],spec["max_tokens"])
    text=rec["text"].strip()
    ok=False; detail=""
    if spec["id"]=="arithmetic":
        ok=(text=="323")
        detail="exact visible answer must equal 323"
    elif spec["id"]=="copy_exact":
        ok=(text=="ALPHA-7-zeta")
        detail="exact copy"
    elif spec["id"]=="json_simple":
        try:
            obj=json.loads(text)
            ok=(obj=={"a":7,"b":"x"})
            detail=f"parsed={obj!r}"
        except Exception as e:
            detail=f"{type(e).__name__}: {e}"
            ok=False
    elif spec["id"]=="comprehension_it":
        ok=(normalize_word(text) in {"martedì","martedi"})
        detail="single-word answer normalized"
    rec.update({"id":spec["id"],"pass":ok,"validation":detail})
    partial["tests"].append(rec)
    atomic(RUN/"quality.partial.json",partial)
    event("SANITY_RESULT",test=spec["id"],passed=ok,finish_reason=rec["finish_reason"])

quality={
  "schema":"mimo26-sanity-v1",
  "status":"PASS" if all(x["pass"] for x in partial["tests"]) else "FAIL",
  "thinking":"disabled_via_chat_template",
  "tests":partial["tests"],
  "completed_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
}
atomic(RUN/"quality.json",quality)
event("QUALITY_PERSISTED",status=quality["status"])

if dist.is_initialized():
    dist.barrier()
