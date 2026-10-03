#!/usr/bin/env python3
from __future__ import annotations
import argparse, fcntl, json, os, signal, subprocess, time
from pathlib import Path

STATE_ROOT=Path("/home/funboy/.local/state/strixhalomimo26/windows")
REL=Path("/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6")
K2=REL/"runtime/ds41/serve-controller.sh"
CLUSTER_LOCK=Path("/home/funboy/.local/state/strix-cluster/compute.lock")

def atomic_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    q=path.with_suffix(path.suffix+".tmp")
    q.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
    os.replace(q,path)

def read_json(path,default=None):
    try:return json.loads(path.read_text())
    except FileNotFoundError:return default

def event(run,kind,**kw):
    rec={"ts":time.time(),"iso":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"event":kind,**kw}
    with (run/"events.jsonl").open("a") as f:
        f.write(json.dumps(rec,sort_keys=True)+"\n"); f.flush(); os.fsync(f.fileno())

def update(run,**kw):
    p=run/"result.json"
    x=read_json(p,{
      "schema":"mimo26-window-result-v1","run_id":run.name,
      "run_completion":"PENDING","initial_cause":None,
      "load":{"status":"NOT_STARTED"},"quality":{"status":"NOT_EVALUATED"},
      "workers":{"rank0":"NOT_STARTED"},"cleanup":{"status":"PENDING"},
    })
    x.update(kw); atomic_json(p,x); return x

def k2status():
    cp=subprocess.run([str(K2),"status"],env={**os.environ,"DS41_ROOT":str(REL)},
                      capture_output=True,text=True)
    try:return json.loads(cp.stdout)
    except:return {"state":"UNKNOWN","rc":cp.returncode,"stdout":cp.stdout,"stderr":cp.stderr}

def unit_state(unit):
    cp=subprocess.run(["systemctl","--user","show",unit,
      "-p","ActiveState","-p","SubState","-p","Result","-p","ExecMainStatus",
      "-p","InvocationID","--no-pager"],capture_output=True,text=True)
    out={}
    for line in cp.stdout.splitlines():
        if "=" in line:
            k,v=line.split("=",1);out[k]=v
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("run_id");a=ap.parse_args()
    run=STATE_ROOT/a.run_id; cfg=read_json(run/"config.json")
    if cfg is None: raise SystemExit(2)
    lock=(run/"run.lock").open("w")
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        update(run,run_completion="DUPLICATE_REJECTED",initial_cause="RUN_LOCK_BUSY");return 90
    launches=run/"launch-count.txt"
    n=int(launches.read_text().strip() or "0") if launches.exists() else 0
    launches.write_text(str(n+1)+"\n")
    if n:
        update(run,run_completion="DUPLICATE_REJECTED",initial_cause="RUN_ID_ALREADY_USED");return 91

    update(run,run_completion="RUNNING",initial_cause=None,
           load={"status":"NOT_STARTED"},quality={"status":"NOT_EVALUATED"},
           workers={"rank0":"NOT_STARTED"},cleanup={"status":"PENDING"})
    event(run,"RUN_START",pid=os.getpid())

    def sig(sig,frame):
        event(run,"COORDINATOR_SIGNAL",signal=sig)
        cur=read_json(run/"result.json",{})
        if cur.get("initial_cause") is None:
            update(run,run_completion="INTERRUPTED",initial_cause="COORDINATOR_INTERRUPTED")
        raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,sig); signal.signal(signal.SIGINT,sig)

    pre=k2status(); atomic_json(run/"k2-before.json",pre); event(run,"K2_PRESTATE",state=pre.get("state"))
    if pre.get("state") not in cfg.get("allowed_k2_states",["READY","OFF"]):
        update(run,run_completion="BLOCKED",initial_cause=f"K2_UNSAFE_{pre.get('state')}");return 20
    if cfg.get("real_k2",True) and pre.get("state")!="OFF":
        event(run,"K2_QUIESCE_START")
        try:
            cp=subprocess.run([str(K2),"off"],env={**os.environ,"DS41_ROOT":str(REL)},
                              capture_output=True,text=True,
                              timeout=float(cfg.get("quiesce_timeout_sec",180)))
        except subprocess.TimeoutExpired:
            update(run,run_completion="FAILED",initial_cause="K2_QUIESCE_TIMEOUT");return 21
        (run/"k2-off.stdout").write_text(cp.stdout);(run/"k2-off.stderr").write_text(cp.stderr)
        post=k2status();atomic_json(run/"k2-off-status.json",post)
        if post.get("state")!="OFF":
            update(run,run_completion="FAILED",initial_cause="K2_QUIESCE_FAILED");return 22
        event(run,"K2_QUIESCED")

    if cfg.get("use_compute_lock",True):
        clock=CLUSTER_LOCK.open("w")
        try:fcntl.flock(clock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            update(run,run_completion="FAILED",initial_cause="COMPUTE_LOCK_BUSY");return 23
        (run/"compute-lock-held").write_text(str(os.getpid())+"\n")
        event(run,"COMPUTE_LOCK_ACQUIRED")
    else:event(run,"COMPUTE_LOCK_SKIPPED_FOR_TEST")

    r0=cfg["rank0"]
    cmd=["systemd-run","--user",f"--unit={r0['unit']}",
         "--property=KillMode=control-group","--property=Restart=no",
         f"--property=RuntimeMaxSec={int(cfg['worker_runtime_sec'])}",
         f"--property=TimeoutStopSec={int(cfg['worker_stop_sec'])}",
         f"--property=StandardOutput=append:{run/'rank0.log'}",
         f"--property=StandardError=append:{run/'rank0.log'}","--",*r0["argv"]]
    try:cp=subprocess.run(cmd,capture_output=True,text=True,check=True)
    except subprocess.CalledProcessError as e:
        (run/"rank0-start.txt").write_text((e.stdout or "")+(e.stderr or ""))
        update(run,run_completion="FAILED",initial_cause="LAUNCH_RANK0_FAILED")
        event(run,"RANK0_LAUNCH_FAILED",rc=e.returncode);return 24
    (run/"rank0-start.txt").write_text(cp.stdout+cp.stderr)
    s0=unit_state(r0["unit"]);atomic_json(run/"rank0-unit-start.json",s0)
    event(run,"RANK0_STARTED",invocation=s0.get("InvocationID"))
    update(run,workers={"rank0":"RUNNING"},load={"status":"IN_PROGRESS"})

    deadline=time.monotonic()+float(cfg["work_timeout_sec"])
    while time.monotonic()<deadline:
        s0=unit_state(r0["unit"])
        lp=run/"load.json"
        if lp.exists():
            l=read_json(lp,{})
            cur=read_json(run/"result.json",{})
            if cur.get("load")!=l:
                cur["load"]=l;atomic_json(run/"result.json",cur);event(run,"LOAD_OBSERVED",status=l.get("status"))
        qp=run/"quality.json"
        if qp.exists():
            q=read_json(qp,{})
            cur=read_json(run/"result.json",{})
            if cur.get("quality")!=q:
                cur["quality"]=q;atomic_json(run/"result.json",cur);event(run,"QUALITY_OBSERVED",status=q.get("status"))
        if s0.get("ActiveState") in {"inactive","failed"}:
            time.sleep(1);s0=unit_state(r0["unit"]);atomic_json(run/"rank0-unit-final.json",s0)
            rc=int(s0.get("ExecMainStatus") or 255);update(run,workers={"rank0":s0})
            if rc==0:
                q=read_json(run/"quality.json",{"status":"NOT_EVALUATED"})
                if q.get("status")=="NOT_EVALUATED":
                    update(run,run_completion="FAILED",initial_cause="QUALITY_MISSING",quality=q);return 31
                update(run,run_completion="PASS",initial_cause="NORMAL_COMPLETION",quality=q)
                event(run,"WORK_COMPLETE",r0=0);return 0
            update(run,run_completion="FAILED",initial_cause=f"WORKER_EXIT_R0_{rc}")
            event(run,"WORKER_FAILURE",r0=rc);return 32
        time.sleep(float(cfg.get("poll_sec",1)))
    update(run,run_completion="TIMEOUT",initial_cause="WORK_TIMEOUT")
    event(run,"WORK_TIMEOUT",seconds=cfg["work_timeout_sec"]);return 124

if __name__=="__main__": raise SystemExit(main())
