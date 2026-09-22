#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, signal, time
from pathlib import Path
BASE=Path("/home/funboy/.local/state/strixhalomimo26/runner-tests")
def atomic(p,obj):
    q=p.with_suffix(p.suffix+".tmp"); q.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n"); os.replace(q,p)
def event(run,kind,**kw):
    rec={"ts":time.time(),"iso":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"event":kind,**kw}
    with (run/"events.jsonl").open("a") as f: f.write(json.dumps(rec,sort_keys=True)+"\n")
ap=argparse.ArgumentParser(); ap.add_argument("run_id"); a=ap.parse_args()
run=BASE/a.run_id
event(run,"CLEANUP_START")
pidp=run/"worker.pid"
if pidp.exists():
    try:
        pid=int(pidp.read_text().strip())
        os.kill(pid,0)
    except (ValueError,ProcessLookupError,PermissionError):
        pass
    else:
        try: os.kill(pid,signal.SIGTERM)
        except ProcessLookupError: pass
# fake controller restore only; never touches DS41.
(run/"fake-controller-state.txt").write_text("READY\n")
p=run/"result.json"
x=json.loads(p.read_text()) if p.exists() else {
 "schema":"mimo26-window-runner-selftest-v1","run_id":a.run_id,
 "run_completion":"UNKNOWN","initial_cause":"UNKNOWN",
 "quality":{"status":"NOT_EVALUATED"}
}
x["cleanup"]={"status":"PASS","controller":"FAKE_READY","at":time.strftime("%Y-%m-%dT%H:%M:%S%z")}
atomic(p,x)
event(run,"CLEANUP_PASS")
