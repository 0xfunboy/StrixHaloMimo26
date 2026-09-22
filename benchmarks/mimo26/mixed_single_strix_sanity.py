#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

RUN=Path(os.environ["MIMO26_MIXED_RUN"])
SERVER=Path(os.environ["MIMO26_LLAMA_SERVER"])
MODEL=Path(os.environ["MIMO26_MIXED_MODEL"])
PORT=int(os.environ.get("MIMO26_MIXED_PORT","18090"))
CTX=int(os.environ.get("MIMO26_MIXED_CTX","4096"))
QUALITY=RUN/"quality.json"
LOAD=RUN/"load.json"
FULL=RUN/"mixed-result.json"
SERVER_LOG=RUN/"llama-server.log"
RUN.mkdir(parents=True,exist_ok=True)


def atomic(path:Path,obj:object)->None:
    q=path.with_suffix(path.suffix+".tmp")
    q.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n")
    os.replace(q,path)


def mem_snapshot()->dict:
    info={}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" in line:
            k,v=line.split(":",1); info[k]=v.strip()
    return {
      "MemTotal":info.get("MemTotal"),"MemAvailable":info.get("MemAvailable"),
      "SwapTotal":info.get("SwapTotal"),"SwapFree":info.get("SwapFree"),
    }


def proc_snapshot(pid:int)->dict:
    out={"pid":pid}
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith(("VmRSS:","VmSize:","VmSwap:","RssAnon:","RssFile:")):
                k,v=line.split(":",1); out[k]=v.strip()
        stat=Path(f"/proc/{pid}/stat").read_text().split()
        out["minflt"]=int(stat[9]); out["majflt"]=int(stat[11])
    except FileNotFoundError:
        out["exited"]=True
    return out


def http_json(method:str,path:str,payload=None,timeout=120):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}",
        data=data,
        headers={"Content-Type":"application/json"},
        method=method,
    )
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.status,json.loads(r.read().decode())


server=None
def stop_server():
    global server
    if server is None or server.poll() is not None:return
    server.terminate()
    try:server.wait(timeout=20)
    except subprocess.TimeoutExpired:
        server.kill(); server.wait(timeout=10)

def sig(sig,frame):
    stop_server()
    raise SystemExit(128+sig)
signal.signal(signal.SIGTERM,sig); signal.signal(signal.SIGINT,sig)

atomic(LOAD,{"status":"IN_PROGRESS","started_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
             "memory_before":mem_snapshot()})
atomic(QUALITY,{"status":"NOT_EVALUATED","tests":[]})

cmd=[
 str(SERVER),
 "--model",str(MODEL),
 "--ctx-size",str(CTX),
 "--n-gpu-layers","all",
 "--split-mode","none",
 "--device","ROCm0",
 "--host","127.0.0.1",
 "--port",str(PORT),
 "--jinja",
 "--chat-template-kwargs",'{"enable_thinking":false}',
]
start=time.perf_counter()
with SERVER_LOG.open("w") as log:
    server=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
    atomic(RUN/"server-command.json",{"argv":cmd,"pid":server.pid})
    deadline=time.monotonic()+1200
    ready=None
    while time.monotonic()<deadline:
        if server.poll() is not None:
            atomic(LOAD,{"status":"FAIL","cause":"SERVER_EXIT_BEFORE_READY",
                         "exit_code":server.returncode,"memory_after":mem_snapshot(),
                         "process":proc_snapshot(server.pid)})
            raise SystemExit(server.returncode or 31)
        try:
            status,obj=http_json("GET","/health",timeout=2)
            if status==200:
                ready=obj;break
        except Exception:
            pass
        time.sleep(1)
    if ready is None:
        atomic(LOAD,{"status":"FAIL","cause":"READY_TIMEOUT",
                     "memory_after":mem_snapshot(),"process":proc_snapshot(server.pid)})
        raise SystemExit(32)

    load_s=time.perf_counter()-start
    atomic(LOAD,{
        "status":"PASS","load_s":load_s,
        "finished_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "server_health":ready,
        "memory_after_load":mem_snapshot(),
        "process_after_load":proc_snapshot(server.pid),
        "ctx_size":CTX,"gpu_layers":"all","split_mode":"none",
        "device":"ROCm0","mmap_default":True,"mlock":False,
    })

    tests=[
      ("arithmetic","Compute 17*19. Return only the integer.",lambda s:s=="323"),
      ("extract","Read this exact token: ZEBRA-4821. Return only that token.",lambda s:s=="ZEBRA-4821"),
      ("json",'Return only valid JSON with exactly these values: alpha is integer 7 and beta is string "blue".',
        lambda s:isinstance(json.loads(s),dict) and json.loads(s)=={"alpha":7,"beta":"blue"}),
      ("italian","Nel testo seguente il colore dichiarato è cobalto. Rispondi solo con il nome del colore.",
        lambda s:s.casefold()=="cobalto"),
      ("english","Alice is first and Bob is second. Who is second? Return only the name.",
        lambda s:s=="Bob"),
    ]
    results=[]
    atomic(QUALITY,{"status":"IN_PROGRESS","tests":results,
                    "started_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "thinking":False})
    for name,prompt,check in tests:
        req={
          "model":"mimo26-mixed",
          "messages":[{"role":"user","content":prompt}],
          "temperature":0,
          "max_tokens":64,
          "stream":False,
        }
        t0=time.perf_counter()
        status,obj=http_json("POST","/v1/chat/completions",req,timeout=300)
        wall=time.perf_counter()-t0
        choice=obj["choices"][0]
        msg=choice.get("message",{})
        text=(msg.get("content") or "").strip()
        reasoning=msg.get("reasoning_content") or msg.get("reasoning")
        try:
            ok=bool(check(text)); reason="PASS" if ok else "expected_mismatch"
        except Exception as e:
            ok=False; reason=f"check:{type(e).__name__}:{e}"
        rec={
          "name":name,"prompt":prompt,"pass":ok,"reason":reason,
          "text":text,"reasoning":reasoning,"finish_reason":choice.get("finish_reason"),
          "wall_s":wall,"http_status":status,"response":obj,
        }
        results.append(rec)
        atomic(QUALITY,{"status":"IN_PROGRESS","tests":results,
                        "updated_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "thinking":False})
    qpass=all(x["pass"] for x in results)
    qdoc={"status":"PASS" if qpass else "FAIL","tests":results,
          "finished_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"thinking":False}
    atomic(QUALITY,qdoc)
    final={
      "schema":"mimo26-mixed-single-strix-v1",
      "load":json.loads(LOAD.read_text()),"quality":qdoc,
      "memory_after_quality":mem_snapshot(),
      "process_after_quality":proc_snapshot(server.pid),
      "server_command":cmd,
    }
    atomic(FULL,final)
    stop_server()
    raise SystemExit(0 if qpass else 40)
