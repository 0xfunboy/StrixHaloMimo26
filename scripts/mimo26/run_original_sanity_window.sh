#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${1:?run id required}"
ROOT=/home/funboy/StrixHaloMimo26
BASE=/home/funboy/.local/state/strixhalomimo26/perf/runs
RUN="$BASE/$RUN_ID"
CFG="$RUN/window-config.json"
REL=/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6
K2="$REL/runtime/ds41/serve-controller.sh"
V=/home/funboy/StrixHaloClusterGLM/.engine/venv
LOCK=/home/funboy/.local/state/strix-cluster/compute.lock

mkdir -p "$RUN"
test -f "$CFG"

json_get() { jq -r "$1" "$CFG"; }
LOAD_TIMEOUT=$(json_get '.load_timeout_sec')
SANITY_TIMEOUT=$(json_get '.sanity_timeout_sec')
WORKER_RUNTIME=$(json_get '.worker_runtime_sec')
MASTER_PORT=$(json_get '.master_port')
R0_UNIT=$(json_get '.workers[0].unit')
R1_UNIT=$(json_get '.workers[1].unit')
R1_HOST=$(json_get '.workers[1].host')

event() {
  local kind="$1"; shift || true
  KIND="$kind" DETAIL="${*:-}" RUN="$RUN" python3 - <<'PY'
import json,os,time
from pathlib import Path
p=Path(os.environ["RUN"])/"window-events.jsonl"
rec={"ts":time.time(),"iso":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "event":os.environ["KIND"],"detail":os.environ.get("DETAIL","")}
with p.open("a") as f:
    f.write(json.dumps(rec,sort_keys=True)+"\n"); f.flush(); os.fsync(f.fileno())
PY
}

set_result() {
  local completion="$1" cause="$2"
  COMPLETION="$completion" CAUSE="$cause" RUN="$RUN" python3 - <<'PY'
import json,os
from pathlib import Path
p=Path(os.environ["RUN"])/"result.json"
if p.exists(): x=json.loads(p.read_text())
else:
    x={"schema":"mimo26-window-result-v1","run_id":Path(os.environ["RUN"]).name,
       "quality":{"status":"NOT_EVALUATED"},"cleanup":{"status":"PENDING"}}
if not x.get("initial_cause"):
    x["initial_cause"]=os.environ["CAUSE"]
x["run_completion"]=os.environ["COMPLETION"]
q=Path(os.environ["RUN"])/"quality.json"
if q.exists():
    x["quality"]=json.loads(q.read_text())
tmp=p.with_suffix(".json.tmp"); tmp.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n"); os.replace(tmp,p)
PY
}

on_signal() {
  local sig="$1"
  event COORDINATOR_SIGNAL "$sig"
  set_result INTERRUPTED COORDINATOR_INTERRUPTED
  exit 143
}
trap 'on_signal TERM' TERM
trap 'on_signal INT' INT

RUN="$RUN" python3 - <<'PY'
import json,os
from pathlib import Path
p=Path(os.environ["RUN"])/"result.json"
x={"schema":"mimo26-window-result-v1","run_id":Path(os.environ["RUN"]).name,
   "run_completion":"RUNNING","initial_cause":None,
   "quality":{"status":"NOT_EVALUATED"},"cleanup":{"status":"PENDING"}}
q=p.with_suffix(".json.tmp"); q.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n"); os.replace(q,p)
PY

event RUN_START
DS41_ROOT="$REL" "$K2" status > "$RUN/k2-before.json"
KSTATE=$(jq -r .state "$RUN/k2-before.json")
case "$KSTATE" in
  READY|STARTING|ERROR)
    event QUIESCE_K2 "$KSTATE"
    DS41_ROOT="$REL" "$K2" off > "$RUN/k2-off.json"
    ;;
  OFF) ;;
  *)
    set_result FAILED "K2_UNSAFE_STATE_$KSTATE"
    exit 20
    ;;
esac

FINAL=$(DS41_ROOT="$REL" "$K2" status | jq -r .state)
if [ "$FINAL" != OFF ]; then
  set_result FAILED "K2_NOT_OFF_$FINAL"
  exit 21
fi

exec 9>"$LOCK"
if ! flock -n 9; then
  set_result FAILED COMPUTE_LOCK_BUSY
  exit 22
fi
event COMPUTE_LOCK_ACQUIRED

SITE=$("$V/bin/python" -c 'import site; print(site.getsitepackages()[0])')
CORE="$SITE/_rocm_sdk_core"
DEVEL="$SITE/_rocm_sdk_devel"
LIBS="$SITE/_rocm_sdk_libraries"
LD="/usr/lib/x86_64-linux-gnu:$CORE/lib:$DEVEL/lib:$LIBS/lib:$SITE/torch/lib"
ROCM_BIN="$DEVEL/bin:$DEVEL/lib/llvm/bin"
COMMON=(
  "LD_LIBRARY_PATH=$LD"
  "PATH=$ROCM_BIN:$V/bin:/usr/local/bin:/usr/bin:/bin"
  "ROCM_HOME=$DEVEL"
  "ROCM_PATH=$DEVEL"
  "HIP_PATH=$DEVEL"
  "HIP_DEVICE_LIB_PATH=$CORE/lib/llvm/amdgcn/bitcode"
  "AITER_JIT_DIR=/home/funboy/.cache/mimo26/aiter"
  "HIP_VISIBLE_DEVICES=0"
  "ROCR_VISIBLE_DEVICES=0"
  "PYTORCH_ROCM_ARCH=gfx1151"
  "VLLM_TARGET_DEVICE=rocm"
  "VLLM_ROCM_USE_AITER=1"
  "VLLM_ROCM_USE_AITER_MOE=0"
  "HF_HUB_OFFLINE=1"
  "TRANSFORMERS_OFFLINE=1"
  "NCCL_SOCKET_IFNAME==thunderbolt0"
  "GLOO_SOCKET_IFNAME=thunderbolt0"
  "NCCL_NET=Socket"
  "NCCL_IB_DISABLE=1"
  "NCCL_SOCKET_FAMILY=AF_INET"
  "NCCL_MIN_NCHANNELS=1"
  "NCCL_MAX_NCHANNELS=1"
  "NCCL_SOCKET_NTHREADS=1"
  "NCCL_NSOCKS_PERTHREAD=1"
  "NCCL_DEBUG=WARN"
  "VLLM_LOGGING_LEVEL=INFO"
)

mkdir -p /home/funboy/.cache/mimo26/aiter
ssh -o IdentityAgent=none -o BatchMode=yes "$R1_HOST" "mkdir -p '$RUN' /home/funboy/.cache/mimo26/aiter"

systemctl --user stop "$R0_UNIT.service" 2>/dev/null || true
systemctl --user reset-failed "$R0_UNIT.service" 2>/dev/null || true
ssh -o IdentityAgent=none -o BatchMode=yes "$R1_HOST" "systemctl --user stop '$R1_UNIT.service' 2>/dev/null || true; systemctl --user reset-failed '$R1_UNIT.service' 2>/dev/null || true"

event WORKER_LAUNCH_START
ssh -o IdentityAgent=none -o BatchMode=yes "$R1_HOST" "systemd-run --user --unit='$R1_UNIT' --property=KillMode=control-group --property=Restart=no --property=RuntimeMaxSec='$WORKER_RUNTIME' --property=TimeoutStopSec=60 --property='StandardOutput=append:$RUN/rank1.log' --property='StandardError=append:$RUN/rank1.log' /usr/bin/env LD_LIBRARY_PATH='$LD' PATH='$ROCM_BIN:$V/bin:/usr/local/bin:/usr/bin:/bin' ROCM_HOME='$DEVEL' ROCM_PATH='$DEVEL' HIP_PATH='$DEVEL' HIP_DEVICE_LIB_PATH='$CORE/lib/llvm/amdgcn/bitcode' PYTHONPATH='/home/funboy:$CORE/share/amd_smi' AITER_JIT_DIR=/home/funboy/.cache/mimo26/aiter HIP_VISIBLE_DEVICES=0 ROCR_VISIBLE_DEVICES=0 PYTORCH_ROCM_ARCH=gfx1151 VLLM_TARGET_DEVICE=rocm VLLM_ROCM_USE_AITER=1 VLLM_ROCM_USE_AITER_MOE=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 NCCL_SOCKET_IFNAME='=thunderbolt0' GLOO_SOCKET_IFNAME=thunderbolt0 NCCL_NET=Socket NCCL_IB_DISABLE=1 NCCL_SOCKET_FAMILY=AF_INET NCCL_MIN_NCHANNELS=1 NCCL_MAX_NCHANNELS=1 NCCL_SOCKET_NTHREADS=1 NCCL_NSOCKS_PERTHREAD=1 NCCL_DEBUG=WARN VLLM_LOGGING_LEVEL=INFO VLLM_HOST_IP=10.55.0.2 MIMO26_RUN_DIR='$RUN' MIMO26_TP=2 MIMO26_KV_BYTES=1073741824 MIMO26_MAX_LEN=4096 MIMO26_MAX_BATCHED=512 MIMO26_MOE_BACKEND=triton_unfused '$V/bin/torchrun' --nnodes=2 --nproc-per-node=1 --node-rank=1 --master-addr=10.55.0.1 --master-port='$MASTER_PORT' /home/funboy/vllm_sanity_suite_mimo26.py" > "$RUN/rank1-start.txt"

sleep 2
systemd-run --user --unit="$R0_UNIT" --property=KillMode=control-group --property=Restart=no --property=RuntimeMaxSec="$WORKER_RUNTIME" --property=TimeoutStopSec=60 --property="StandardOutput=append:$RUN/rank0.log" --property="StandardError=append:$RUN/rank0.log" /usr/bin/env "${COMMON[@]}" PYTHONPATH="$ROOT/benchmarks/mimo26:$CORE/share/amd_smi" VLLM_HOST_IP=10.55.0.1 MIMO26_RUN_DIR="$RUN" MIMO26_TP=2 MIMO26_KV_BYTES=1073741824 MIMO26_MAX_LEN=4096 MIMO26_MAX_BATCHED=512 MIMO26_MOE_BACKEND=triton_unfused "$V/bin/torchrun" --nnodes=2 --nproc-per-node=1 --node-rank=0 --master-addr=10.55.0.1 --master-port="$MASTER_PORT" "$ROOT/benchmarks/mimo26/vllm_sanity_suite.py" > "$RUN/rank0-start.txt"

systemctl --user show "$R0_UNIT.service" -p InvocationID -p RuntimeMaxUSec -p TimeoutStopUSec -p KillMode --no-pager > "$RUN/rank0-unit.txt"
ssh -o IdentityAgent=none -o BatchMode=yes "$R1_HOST" "systemctl --user show '$R1_UNIT.service' -p InvocationID -p RuntimeMaxUSec -p TimeoutStopUSec -p KillMode --no-pager" > "$RUN/rank1-unit.txt"
event WORKERS_STARTED

deadline=$(( $(date +%s) + LOAD_TIMEOUT ))
while [ ! -s "$RUN/load.json" ]; do
  a=$(systemctl --user is-active "$R0_UNIT.service" 2>/dev/null || true)
  b=$(ssh -o IdentityAgent=none -o BatchMode=yes "$R1_HOST" "systemctl --user is-active '$R1_UNIT.service' 2>/dev/null || true")
  if [[ "$a" =~ ^(inactive|failed)$ || "$b" =~ ^(inactive|failed)$ ]]; then
    set_result FAILED WORKER_EXIT_BEFORE_LOAD
    event WORKER_EXIT_BEFORE_LOAD "r0=$a r1=$b"
    exit 30
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    set_result TIMEOUT LOAD_TIMEOUT
    event LOAD_TIMEOUT "$LOAD_TIMEOUT"
    exit 124
  fi
  sleep 2
done
event LOAD_OBSERVED

deadline=$(( $(date +%s) + SANITY_TIMEOUT ))
while [ ! -s "$RUN/quality.json" ]; do
  a=$(systemctl --user is-active "$R0_UNIT.service" 2>/dev/null || true)
  b=$(ssh -o IdentityAgent=none -o BatchMode=yes "$R1_HOST" "systemctl --user is-active '$R1_UNIT.service' 2>/dev/null || true")
  if [[ "$a" =~ ^(inactive|failed)$ || "$b" =~ ^(inactive|failed)$ ]]; then
    set_result FAILED WORKER_EXIT_BEFORE_QUALITY
    event WORKER_EXIT_BEFORE_QUALITY "r0=$a r1=$b"
    exit 31
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    set_result TIMEOUT SANITY_TIMEOUT
    event SANITY_TIMEOUT "$SANITY_TIMEOUT"
    exit 124
  fi
  sleep 1
done
event QUALITY_OBSERVED "$(jq -r .status "$RUN/quality.json")"

teardown_done=0
for i in $(seq 1 60); do
  a=$(systemctl --user is-active "$R0_UNIT.service" 2>/dev/null || true)
  b=$(ssh -o IdentityAgent=none -o BatchMode=yes "$R1_HOST" "systemctl --user is-active '$R1_UNIT.service' 2>/dev/null || true")
  if [[ "$a" =~ ^(inactive|failed)$ && "$b" =~ ^(inactive|failed)$ ]]; then
    teardown_done=1
    break
  fi
  sleep 1
done
if [ "$teardown_done" != 1 ]; then
  set_result FAILED WORKER_TEARDOWN_TIMEOUT
  event WORKER_TEARDOWN_TIMEOUT
  exit 33
fi

r0=$(systemctl --user show "$R0_UNIT.service" -p ExecMainStatus --value 2>/dev/null || echo 255)
r1=$(ssh -o IdentityAgent=none -o BatchMode=yes "$R1_HOST" "systemctl --user show '$R1_UNIT.service' -p ExecMainStatus --value 2>/dev/null || echo 255")
printf 'r0=%s r1=%s\n' "$r0" "$r1" > "$RUN/worker-status.txt"
if [ "$r0" != 0 ] || [ "$r1" != 0 ]; then
  set_result FAILED "WORKER_EXIT_r0_${r0}_r1_${r1}"
  exit 32
fi

qstatus=$(jq -r .status "$RUN/quality.json")
if [ "$qstatus" = PASS ]; then
  set_result PASS NORMAL_COMPLETION
  event RUN_PASS
  exit 0
else
  set_result QUALITY_FAIL QUALITY_GATE_FAIL
  event QUALITY_FAIL
  exit 2
fi
