#!/usr/bin/env python3
from __future__ import annotations
import argparse, fcntl, json, os, signal, subprocess, sys, time
from pathlib import Path

BASE=Path("/home/funboy/.local/state/strixhalomimo26/runner-tests")

def atomic_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    q=p.with_suffix(p.suffix+".tmp")
    q.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
    os.replace(q,p)

def event(run: Path, kind: str, **kw):
    rec={"ts":time.time(),"iso":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"event":kind,**kw}
    with (run/"events.jsonl").open("a") as f:
        f.write(json.dumps(rec,sort_keys=True)+"\n")
        f.flush(); os.fsync(f.fileno())

def load_result(run: Path):
    p=run/"result.json"
    if p.exists(): return json.loads(p.read_text())
    return {
        "schema":"mimo26-window-runner-selftest-v1",
        "run_id":run.name,
        "run_completion":"RUNNING",
        "initial_cause":None,
        "quality":{"status":"NOT_EVALUATED"},
        "cleanup":{"status":"PENDING"},
    }

def save_result(run: Path, **updates):
    x=load_result(run); x.update(updates); atomic_json(run/"result.json",x)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("run_id"); a=ap.parse_args()
    run=BASE/a.run_id
    cfg=json.loads((run/"config.json").read_text())
    run.mkdir(parents=True,exist_ok=True)
    lock=(run/"run.lock").open("w")
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(90)
    launches=run/"launch-count.txt"
    n=int(launches.read_text() or "0") if launches.exists() else 0
    launches.write_text(str(n+1)+"\n")
    save_result(run,run_completion="RUNNING",initial_cause=None,
                quality={"status":"NOT_EVALUATED"},cleanup={"status":"PENDING"})
    event(run,"RUN_START",scenario=cfg["scenario"],pid=os.getpid())

    child: subprocess.Popen|None=None
    def interrupted(sig,frame):
        nonlocal child
        event(run,"COORDINATOR_SIGNAL",signal=sig)
        x=load_result(run)
        if x.get("initial_cause") is None:
            x["initial_cause"]="COORDINATOR_INTERRUPTED"
            x["run_completion"]="INTERRUPTED"
            atomic_json(run/"result.json",x)
        if child and child.poll() is None:
            child.terminate()
        raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)

    sc=cfg["scenario"]; timeout=float(cfg.get("work_timeout_sec",5))
    worker_code={
      "normal":"import time; time.sleep(0.4); print('QUALITY_OK',flush=True)",
      "worker_error":"import time,sys; time.sleep(0.3); print('WORKER_ERROR',flush=True); sys.exit(7)",
      "timeout":"import time; time.sleep(30)",
      "interrupt":"import time; time.sleep(30)",
    }[sc]
    log=(run/"worker.log").open("w")
    child=subprocess.Popen([sys.executable,"-c",worker_code],stdout=log,stderr=subprocess.STDOUT)
    (run/"worker.pid").write_text(str(child.pid)+"\n")
    event(run,"WORKER_START",pid=child.pid)

    try:
        rc=child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        event(run,"WORK_TIMEOUT",seconds=timeout)
        x=load_result(run)
        x["initial_cause"]="WORK_TIMEOUT"; x["run_completion"]="TIMEOUT"
        atomic_json(run/"result.json",x)
        child.terminate()
        try: child.wait(timeout=1)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait()
        return 124

    event(run,"WORKER_EXIT",rc=rc)
    if rc != 0:
        x=load_result(run)
        x["initial_cause"]=f"WORKER_EXIT_{rc}"; x["run_completion"]="FAILED"
        atomic_json(run/"result.json",x)
        return rc

    if sc=="normal":
        quality={
          "status":"PASS","prompt":"dummy arithmetic","token_ids":[1,2,3],
          "text":"323","finish_reason":"stop"
        }
        atomic_json(run/"quality.json",quality)
        event(run,"QUALITY_PERSISTED")
        x=load_result(run); x["quality"]=quality
        x["initial_cause"]="NORMAL_COMPLETION"; x["run_completion"]="PASS"
        atomic_json(run/"result.json",x)
        return 0
    return 0

if __name__=="__main__":
    raise SystemExit(main())
