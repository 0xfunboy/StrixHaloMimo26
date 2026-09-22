#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/funboy/StrixHaloMimo26
VENV=/home/funboy/.local/share/strixhalomimo26/hf-venv
HF="$VENV/bin/hf"
PY="$VENV/bin/python"
VERIFY="$ROOT/scripts/mimo26/verify_hf_snapshot.py"
STATE_DIR=/home/funboy/.local/state/strixhalomimo26
REGISTRY="$STATE_DIR/download-state.json"
LOCK="$STATE_DIR/download.lock"
MODEL_ROOT=/home/funboy/models/MiMo-V2.6

OFF_REPO='XiaomiMiMo/MiMo-V2.6-Flash-RL'
OFF_REV='5711b268169967567844e1e560e8a3966da959b1'
OFF_DIR="$MODEL_ROOT/official/MiMo-V2.6-Flash-RL"
OFF_MD="$ROOT/docs/mimo26/MIMO26_MODEL_OFFICIAL_MANIFEST.md"
OFF_SHA="$ROOT/docs/mimo26/manifests/mimo26-official.sha256"
OFF_FILES="$ROOT/docs/mimo26/manifests/mimo26-official-files.tsv"

MIX_REPO='Baekpica/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF'
MIX_DIR="$MODEL_ROOT/mixed-gguf/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF"
MIX_MD="$ROOT/docs/mimo26/MIMO26_MODEL_MIXED_GGUF_MANIFEST.md"
MIX_SHA="$ROOT/docs/mimo26/manifests/mimo26-mixed-gguf.sha256"
MIX_FILES="$ROOT/docs/mimo26/manifests/mimo26-mixed-gguf-files.tsv"
MIX_GATE="$ROOT/runtime/mimo26/mixed-gguf-gate.json"

mkdir -p "$STATE_DIR" "$OFF_DIR" "$MIX_DIR" "$(dirname "$OFF_SHA")"
exec 9>"$LOCK"
if ! flock -n 9; then
    echo "another StrixHaloMimo26 download runner owns $LOCK" >&2
    exit 9
fi

atomic_state() {
    local phase="$1" model1="$2" model2="$3" detail="${4:-}"
    PHASE="$phase" MODEL1="$model1" MODEL2="$model2" DETAIL="$detail" "$PY" - "$REGISTRY" <<'PY'
import json, os, sys, time
from pathlib import Path
p=Path(sys.argv[1])
obj={
 "schema":"strixhalomimo26-download-v1",
 "phase":os.environ["PHASE"],
 "model1":os.environ["MODEL1"],
 "model2":os.environ["MODEL2"],
 "detail":os.environ.get("DETAIL",""),
 "pid":os.getppid(),
 "updated_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
}
q=p.with_suffix(p.suffix+".tmp")
q.write_text(json.dumps(obj,indent=2)+"\n")
os.replace(q,p)
PY
}

free_bytes() {
    df -B1 --output=avail /home/funboy | tail -1 | tr -d ' '
}

initial_gate() {
    if [[ -f "$OFF_DIR/.mimo26-verified.json" ]]; then
        return 0
    fi
    local free
    free="$(free_bytes)"
    if (( free < 350 * 1024 * 1024 * 1024 )); then
        atomic_state PREFLIGHT FAILED NOT_STARTED "free bytes $free below 350 GiB initial gate"
        echo "insufficient initial free space: $free bytes" >&2
        exit 10
    fi
}

verify_official() {
    "$PY" "$VERIFY" \
      --repo "$OFF_REPO" --revision "$OFF_REV" --local-dir "$OFF_DIR" \
      --label 'MiMo-V2.6 official Flash-RL' \
      --manifest-md "$OFF_MD" --sha-manifest "$OFF_SHA" --files-manifest "$OFF_FILES"
}

gate_mixed() {
    "$PY" - "$MIX_REPO" "$MIX_GATE" <<'PY'
from huggingface_hub import HfApi
from pathlib import Path
import json, os, sys, time
repo=sys.argv[1]; out=Path(sys.argv[2])
info=HfApi().model_info(repo, files_metadata=True)
files=[]
ggufs=[]
total=0
for s in info.siblings:
    size=int(s.size or 0); total+=size
    files.append({"path":s.rfilename,"size":size})
    if s.rfilename.lower().endswith(".gguf"):
        ggufs.append({"path":s.rfilename,"size":size})
obj={
 "schema":"mimo26-mixed-gguf-gate-v1",
 "repo":repo,
 "revision":info.sha,
 "files":len(files),
 "total_bytes":total,
 "gguf_count":len(ggufs),
 "ggufs":ggufs,
 "status":"AVAILABLE" if ggufs else "WAITING_UPSTREAM",
 "checked_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
}
out.parent.mkdir(parents=True,exist_ok=True)
tmp=out.with_suffix(out.suffix+".tmp")
tmp.write_text(json.dumps(obj,indent=2)+"\n")
os.replace(tmp,out)
print(json.dumps(obj))
PY
}

initial_gate
export HF_XET_CACHE="$MODEL_ROOT/.xet-cache"
export HF_HUB_DISABLE_PROGRESS_BARS=0

if [[ ! -f "$OFF_DIR/.mimo26-verified.json" ]]; then
    atomic_state DOWNLOAD_1 IN_PROGRESS NOT_STARTED "official pinned revision $OFF_REV"
    "$HF" download "$OFF_REPO" --revision "$OFF_REV" --local-dir "$OFF_DIR"
    atomic_state VERIFY_1 VERIFYING NOT_STARTED "listing/size/full sha256"
    verify_official
else
    echo "official model already verified; skipping download #1"
fi

atomic_state GATE_2 COMPLETE CHECKING "query mixed GGUF only after official COMPLETE"
gate_mixed
gguf_count="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["gguf_count"])' "$MIX_GATE")"
mix_rev="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["revision"])' "$MIX_GATE")"

if [[ "$gguf_count" == "0" ]]; then
    atomic_state COMPLETE COMPLETE WAITING_UPSTREAM "no .gguf files in upstream listing at $mix_rev"
    exit 0
fi

if [[ ! -f "$MIX_DIR/.mimo26-verified.json" ]]; then
    expected_bytes="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["total_bytes"])' "$MIX_GATE")"
    free="$(free_bytes)"
    reserve=$((50 * 1024 * 1024 * 1024))
    if (( free < expected_bytes + reserve )); then
        atomic_state DOWNLOAD_2 COMPLETE FAILED "insufficient free bytes $free for expected $expected_bytes plus 50 GiB reserve"
        exit 11
    fi
    atomic_state DOWNLOAD_2 COMPLETE IN_PROGRESS "mixed GGUF revision $mix_rev"
    "$HF" download "$MIX_REPO" --revision "$mix_rev" --local-dir "$MIX_DIR"
    atomic_state VERIFY_2 COMPLETE VERIFYING "listing/size/full sha256"
    "$PY" "$VERIFY" \
      --repo "$MIX_REPO" --revision "$mix_rev" --local-dir "$MIX_DIR" \
      --label 'MiMo-V2.6 mixed GGUF' \
      --manifest-md "$MIX_MD" --sha-manifest "$MIX_SHA" --files-manifest "$MIX_FILES"
fi

atomic_state COMPLETE COMPLETE COMPLETE "both targets verified"
