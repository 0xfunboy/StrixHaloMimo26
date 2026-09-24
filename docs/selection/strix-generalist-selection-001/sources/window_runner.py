#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

from window_guards import preflight

STATE_ROOT=Path("/home/funboy/.local/state/strixhalomimo26/windows")
REL=Path("/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6")
K2=REL/"runtime/ds41/serve-controller.sh"
CLUSTER_LOCK=Path("/home/funboy/.local/state/strix-cluster/compute.lock")


def atomic_json(path:Path,obj:object)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
    os.replace(tmp,path)


def read_json(path:Path,default=None):
    try: return json.loads(path.read_text())
    except FileNotFoundError: return default


def event(run:Path,kind:str,**kw)->None:
    rec={"ts":time.time(),"iso":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"event":kind,**kw}
    with (run/"events.jsonl").open("a") as f:
        f.write(json.dumps(rec,sort_keys=True)+"\n")
        f.flush(); os.fsync(f.fileno())


def update_result(run:Path,**updates)->dict:
    p=run/"result.json"
    cur=read_json(p,{
        "schema":"mimo26-window-result-v1",
        "run_id":run.name,
        "run_completion":"PENDING",
        "initial_cause":None,
        "load":{"status":"NOT_STARTED"},
        "quality":{"status":"NOT_EVALUATED"},
        "workers":{"rank0":"NOT_STARTED","rank1":"NOT_STARTED"},
        "cleanup":{"status":"PENDING"},
    })
    cur.update(updates)
    atomic_json(p,cur)
    return cur


def k2_status()->dict:
    cp=subprocess.run(
        [str(K2),"status"],
        env={**os.environ,"DS41_ROOT":str(REL)},
        capture_output=True,text=True,timeout=30,
    )
    try: return json.loads(cp.stdout)
    except Exception: return {"state":"UNKNOWN","rc":cp.returncode,"stdout":cp.stdout,"stderr":cp.stderr}


def run_cmd(cmd:list[str],timeout:float|None=30,**kw):
    return subprocess.run(cmd,timeout=timeout,**kw)


def unit_state_local(unit:str)->dict:
    cp=run_cmd(["systemctl","--user","show",unit,
        "-p","ActiveState","-p","SubState","-p","Result","-p","ExecMainStatus",
        "-p","InvocationID","--no-pager"],capture_output=True,text=True)
    out={}
    for line in cp.stdout.splitlines():
        if "=" in line:
            k,v=line.split("=",1); out[k]=v
    return out


def unit_state_remote(unit:str)->dict:
    cp=run_cmd(["ssh","-o","IdentityAgent=none","-o","BatchMode=yes","02-evo-x3-tb",
        "systemctl","--user","show",unit,
        "-p","ActiveState","-p","SubState","-p","Result","-p","ExecMainStatus",
        "-p","InvocationID","--no-pager"],capture_output=True,text=True)
    out={}
    for line in cp.stdout.splitlines():
        if "=" in line:
            k,v=line.split("=",1); out[k]=v
    return out


def terminal_decision(s0, s1, has_peer):
    terminal0=s0.get("ActiveState") in {"inactive","failed"}
    terminal1=has_peer and s1.get("ActiveState") in {"inactive","failed"}
    failed0=terminal0 and (s0.get("Result") not in {"success",""} or s0.get("ExecMainStatus") not in {"0",None,""})
    failed1=terminal1 and (s1.get("Result") not in {"success",""} or s1.get("ExecMainStatus") not in {"0",None,""})
    if failed0 or failed1:return "FAIL"
    if terminal0 and (not has_peer or terminal1):return "COMPLETE"
    return "WAIT"


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("run_id"); a=ap.parse_args()
    if not a.run_id.startswith("generalist-selection-001-"):
        raise ValueError("not a selection campaign run")
    run=STATE_ROOT/a.run_id
    cfg=read_json(run/"config.json")
    if cfg is None: raise SystemExit(f"missing config: {run/'config.json'}")
    run.mkdir(parents=True,exist_ok=True)

    # Per-run idempotency lock. Readback/reconnect never launches another copy.
    rlock=(run/"run.lock").open("a")
    try: fcntl.flock(rlock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        return 90

    launches=run/"launch-count.txt"
    n=int(launches.read_text().strip() or "0") if launches.exists() else 0
    if n:
        return 91
    with launches.open("x") as f:
        f.write("1\n"); f.flush(); os.fsync(f.fileno())

    event(run,"RUN_START",pid=os.getpid())
    update_result(run,run_completion="RUNNING",initial_cause=None,
                  load={"status":"NOT_STARTED"},quality={"status":"NOT_EVALUATED"},
                  workers={"rank0":"NOT_STARTED","rank1":"NOT_STARTED"},
                  cleanup={"status":"PENDING"})

    terminating=False
    def on_signal(sig,frame):
        nonlocal terminating
        if terminating: return
        terminating=True
        event(run,"COORDINATOR_SIGNAL",signal=sig)
        cur=read_json(run/"result.json",{})
        if cur.get("initial_cause") is None:
            update_result(run,initial_cause="COORDINATOR_INTERRUPTED",
                          run_completion="INTERRUPTED")
        raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,on_signal); signal.signal(signal.SIGINT,on_signal)

    try:
        admission=preflight(Path(cfg["campaign_root"]),run,cfg)
    except Exception as exc:
        update_result(run,run_completion="BLOCKED",initial_cause="ADMISSION:"+str(exc))
        return 19
    pre=admission["controller"]
    atomic_json(run/"k2-before.json",pre)
    event(run,"K2_PRESTATE",state=pre.get("state"))
    allowed=cfg.get("allowed_k2_states",["READY","OFF"])
    if pre.get("state") not in allowed:
        update_result(run,run_completion="BLOCKED",
                      initial_cause=f"K2_UNSAFE_{pre.get('state')}")
        return 20

    if cfg.get("real_k2",True) and pre.get("state")!="OFF":
        event(run,"K2_QUIESCE_START")
        cp=run_cmd([str(K2),"off"],env={**os.environ,"DS41_ROOT":str(REL)},
                   capture_output=True,text=True,
                   timeout=float(cfg.get("quiesce_timeout_sec",180)))
        (run/"k2-off.stdout").write_text(cp.stdout); (run/"k2-off.stderr").write_text(cp.stderr)
        post=k2_status(); atomic_json(run/"k2-off-status.json",post)
        if post.get("state")!="OFF":
            update_result(run,run_completion="FAILED",initial_cause="K2_QUIESCE_FAILED")
            return 21
        event(run,"K2_QUIESCED")

    clock=None
    if cfg.get("use_compute_lock", True):
        clock=CLUSTER_LOCK.open("a")
        try: fcntl.flock(clock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            update_result(run,run_completion="FAILED",initial_cause="COMPUTE_LOCK_BUSY")
            return 22
        (run/"compute-lock-held").write_text(str(os.getpid())+"\n")
        event(run,"COMPUTE_LOCK_ACQUIRED")
    else:
        event(run,"COMPUTE_LOCK_SKIPPED_FOR_TEST")

    r0=cfg["rank0"]
    r1=cfg.get("rank1")
    if not isinstance(r0.get("argv"),list):
        raise ValueError("rank0 argv must be list")
    if r1 is not None and not isinstance(r1.get("argv"),list):
        raise ValueError("rank1 argv must be list or rank1 must be null")

    if r1 is not None:
        # Start rank1 remotely first for distributed windows.
        run_cmd(["ssh","-o","IdentityAgent=none","-o","BatchMode=yes","02-evo-x3-tb",
            "mkdir","-p",str(run)],check=True)
        remote_cmd=[
            "systemd-run","--user",f"--unit={r1['unit']}",
            "--property=KillMode=control-group","--property=Restart=no",
            f"--property=RuntimeMaxSec={int(cfg['worker_runtime_sec'])}",
            f"--property=TimeoutStopSec={int(cfg['worker_stop_sec'])}",
            f"--property=StandardOutput=append:{run/'rank1.log'}",
            f"--property=StandardError=append:{run/'rank1.log'}",
            "--",
            *r1["argv"],
        ]
        remote_command = " ".join(shlex.quote(x) for x in remote_cmd)
        try:
            cp=run_cmd(["ssh","-o","IdentityAgent=none","-o","BatchMode=yes",
                        "02-evo-x3-tb", remote_command],
                       capture_output=True,text=True,check=True)
        except subprocess.CalledProcessError as e:
            (run/"rank1-start.txt").write_text((e.stdout or "")+(e.stderr or ""))
            update_result(run,run_completion="FAILED",initial_cause="LAUNCH_RANK1_FAILED")
            event(run,"RANK1_LAUNCH_FAILED",rc=e.returncode)
            return 23
        (run/"rank1-start.txt").write_text(cp.stdout+cp.stderr)
        s1=unit_state_remote(r1["unit"])
        atomic_json(run/"rank1-unit-start.json",s1)
        event(run,"RANK1_STARTED",invocation=s1.get("InvocationID"))
        time.sleep(float(cfg.get("rank_stagger_sec",2)))
    else:
        s1={"ActiveState":"not-applicable","SubState":"not-applicable",
            "Result":"not-applicable","ExecMainStatus":"0","InvocationID":""}
        atomic_json(run/"rank1-unit-start.json",s1)
        event(run,"RANK1_NOT_APPLICABLE")

    local_cmd=[
        "systemd-run","--user",f"--unit={r0['unit']}",
        "--property=KillMode=control-group","--property=Restart=no",
        f"--property=RuntimeMaxSec={int(cfg['worker_runtime_sec'])}",
        f"--property=TimeoutStopSec={int(cfg['worker_stop_sec'])}",
        f"--property=StandardOutput=append:{run/'rank0.log'}",
        f"--property=StandardError=append:{run/'rank0.log'}",
        "--",
        *r0["argv"],
    ]
    try:
        cp=run_cmd(local_cmd,capture_output=True,text=True,check=True)
    except subprocess.CalledProcessError as e:
        (run/"rank0-start.txt").write_text((e.stdout or "")+(e.stderr or ""))
        update_result(run,run_completion="FAILED",initial_cause="LAUNCH_RANK0_FAILED")
        event(run,"RANK0_LAUNCH_FAILED",rc=e.returncode)
        return 24
    (run/"rank0-start.txt").write_text(cp.stdout+cp.stderr)
    s0=unit_state_local(r0["unit"]); atomic_json(run/"rank0-unit-start.json",s0)
    event(run,"RANK0_STARTED",invocation=s0.get("InvocationID"))
    update_result(
        run,
        workers={"rank0":"RUNNING","rank1":"RUNNING" if r1 is not None else "NOT_APPLICABLE"},
        load={"status":"IN_PROGRESS"},
    )

    deadline=time.monotonic()+float(cfg["work_timeout_sec"])
    while time.monotonic()<deadline:
        s0=unit_state_local(r0["unit"])
        if r1 is not None:
            s1=unit_state_remote(r1["unit"])
        else:
            s1={"ActiveState":"not-applicable","SubState":"not-applicable",
                "Result":"not-applicable","ExecMainStatus":"0","InvocationID":""}
        lpath=run/"load.json"
        if lpath.exists():
            l=read_json(lpath,{})
            cur=read_json(run/"result.json",{})
            if cur.get("load") != l:
                cur["load"]=l; atomic_json(run/"result.json",cur)
                event(run,"LOAD_OBSERVED",status=l.get("status"))
        qpath=run/"quality.json"
        if qpath.exists():
            q=read_json(qpath,{})
            cur=read_json(run/"result.json",{})
            if cur.get("quality") != q:
                cur["quality"]=q
                atomic_json(run/"result.json",cur)
                event(run,"QUALITY_OBSERVED",status=q.get("status"),
                      tests_completed=len(q.get("tests",[])))
        decision=terminal_decision(s0,s1,r1 is not None)
        all_terminal=decision=="COMPLETE"
        if decision!="WAIT":
            time.sleep(1)
            s0=unit_state_local(r0["unit"])
            if r1 is not None:
                s1=unit_state_remote(r1["unit"])
            else:
                s1={"ActiveState":"not-applicable","SubState":"not-applicable",
                    "Result":"not-applicable","ExecMainStatus":"0","InvocationID":""}
            atomic_json(run/"rank0-unit-final.json",s0)
            atomic_json(run/"rank1-unit-final.json",s1)
            r0rc=int(s0.get("ExecMainStatus") or 255)
            r1rc=int(s1.get("ExecMainStatus") or 0) if r1 is not None else 0
            final_quality=read_json(run/"quality.json",{"status":"NOT_EVALUATED"})
            final_load=read_json(run/"load.json",{"status":"NOT_EVALUATED"})
            update_result(run,workers={"rank0":s0,"rank1":s1},
                          quality=final_quality,load=final_load)
            if r0rc==0 and r1rc==0 and all_terminal:
                quality=final_quality
                if quality.get("status")!="PASS" or final_load.get("status")!="PASS" or not (run/"arm-result.json").exists():
                    update_result(run,run_completion="FAILED",initial_cause="QUALITY_MISSING",
                                  quality=quality)
                    return 31
                update_result(run,run_completion="PASS",initial_cause="NORMAL_COMPLETION",
                              quality=quality)
                event(run,"WORK_COMPLETE",r0=r0rc,r1=r1rc)
                return 0
            cause=f"WORKER_EXIT_R0_{r0rc}_R1_{r1rc}"
            update_result(run,run_completion="FAILED",initial_cause=cause)
            event(run,"WORKER_FAILURE",r0=r0rc,r1=r1rc)
            return 32
        time.sleep(float(cfg.get("poll_sec",1)))

    update_result(run,run_completion="TIMEOUT",initial_cause="WORK_TIMEOUT")
    event(run,"WORK_TIMEOUT",seconds=cfg["work_timeout_sec"])
    return 124

if __name__=="__main__":
    raise SystemExit(main())
