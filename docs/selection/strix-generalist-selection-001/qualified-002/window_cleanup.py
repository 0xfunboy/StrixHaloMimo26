#!/usr/bin/env python3
from __future__ import annotations
import argparse, fcntl, json, os, subprocess, time
from pathlib import Path
STATE_ROOT=Path("/home/funboy/.local/state/strixhalomimo26/windows")
REL=Path("/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6")
K2=REL/"runtime/ds41/serve-controller.sh"
LOCK=Path("/home/funboy/.local/state/strixhalomimo26/cleanup-global.lock")

def atomic(path,obj):
    q=path.with_suffix(path.suffix+".tmp"); q.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n"); os.replace(q,path)
def read(path,default=None):
    try:return json.loads(path.read_text())
    except FileNotFoundError:return default
def event(run,kind,**kw):
    rec={"ts":time.time(),"iso":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"event":kind,**kw}
    with (run/"events.jsonl").open("a") as f:f.write(json.dumps(rec,sort_keys=True)+"\n")
def k2status():
    cp=subprocess.run([str(K2),"status"],env={**os.environ,"DS41_ROOT":str(REL)},capture_output=True,text=True)
    try:return json.loads(cp.stdout)
    except:return {"state":"UNKNOWN","rc":cp.returncode}
ap=argparse.ArgumentParser();ap.add_argument("run_id");a=ap.parse_args()
run=STATE_ROOT/a.run_id; cfg=read(run/"config.json",{})
LOCK.parent.mkdir(parents=True,exist_ok=True)
lf=LOCK.open("w"); fcntl.flock(lf,fcntl.LOCK_EX)
event(run,"CLEANUP_START")
# Stop workers idempotently.
r0=(cfg.get("rank0") or {}).get("unit")
r1=(cfg.get("rank1") or {}).get("unit")
if r0:
    subprocess.run(["systemctl","--user","stop",r0],timeout=float(cfg.get("worker_stop_sec",30)),check=False)
    subprocess.run(["systemctl","--user","reset-failed",r0],check=False)
if r1:
    subprocess.run(["ssh","-o","IdentityAgent=none","-o","BatchMode=yes","02-evo-x3-tb",
                    "systemctl","--user","stop",r1],timeout=float(cfg.get("worker_stop_sec",30)),check=False)
    subprocess.run(["ssh","-o","IdentityAgent=none","-o","BatchMode=yes","02-evo-x3-tb",
                    "systemctl","--user","reset-failed",r1],check=False)
(run/"compute-lock-held").unlink(missing_ok=True)

restore={"status":"SKIPPED","k2_state":None}
pre=read(run/"k2-before.json",{})
if cfg.get("real_k2",True) and pre.get("state")!="OFF":
    budget=float(cfg.get("restore_timeout_sec",900)); deadline=time.monotonic()+budget
    while time.monotonic()<deadline:
        st=k2status(); state=st.get("state")
        if state=="READY":
            restore={"status":"PASS","k2_state":"READY"}; break
        if state in {"OFF","ERROR"}:
            try:
                subprocess.run([str(K2),"on"],env={**os.environ,"DS41_ROOT":str(REL)},
                               timeout=min(300,max(1,deadline-time.monotonic())),
                               capture_output=True,text=True,check=False)
            except subprocess.TimeoutExpired: pass
        time.sleep(3)
    else:
        restore={"status":"FAIL","k2_state":k2status().get("state")}
else:
    restore={"status":"PASS","k2_state":pre.get("state","OFF"),"note":"prestate did not require restore"}

res=read(run/"result.json",{
 "schema":"mimo26-window-result-v1","run_id":run.name,
 "run_completion":"UNKNOWN","initial_cause":"UNKNOWN",
 "quality":{"status":"NOT_EVALUATED"},
})
res["cleanup"]={**restore,"at":time.strftime("%Y-%m-%dT%H:%M:%S%z")}
atomic(run/"result.json",res)
atomic(run/"k2-after.json",k2status())
event(run,"CLEANUP_DONE",**restore)
