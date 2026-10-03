#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/funboy/StrixHaloMimo26
STATE=/home/funboy/.local/state/strixhalomimo26/mixed
LOCK="$STATE/download.lock"
REG="$STATE/state.json"
LOGIC_REV=b3794b22b6276f8120c340f52639f5eaa354a3fd
REPO=Baekpica/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF
PREFIX=MQ-IQ2-XXS-XS-Q8-MM-BF16
DEST=/home/funboy/models/MiMo-V2.6/mixed-gguf/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF
V=/home/funboy/.local/share/strixhalomimo26/hf-venv
mkdir -p "$STATE" "$DEST"
exec 9>"$LOCK"
flock -n 9 || { echo MIXED_DOWNLOAD_ALREADY_RUNNING; exit 9; }

state() {
  local phase="$1" status="$2" detail="${3:-}"
  PHASE="$phase" STATUS="$status" DETAIL="$detail" "$V/bin/python" - "$REG" <<'PY'
import json,os,sys,time
from pathlib import Path
p=Path(sys.argv[1]); q=p.with_suffix('.tmp')
x={
 'schema':'mimo26-mixed-download-v1',
 'repo':'Baekpica/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF',
 'revision':'b3794b22b6276f8120c340f52639f5eaa354a3fd',
 'variant':'MQ-IQ2-XXS-XS-Q8-MM-BF16',
 'destination':'/home/funboy/models/MiMo-V2.6/mixed-gguf/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF',
 'phase':os.environ['PHASE'],'status':os.environ['STATUS'],
 'detail':os.environ.get('DETAIL',''),
 'pid':os.getppid(),'updated_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
}
q.write_text(json.dumps(x,indent=2)+'\n'); os.replace(q,p)
PY
}

free=$(df -B1 --output=avail /home/funboy | tail -1 | tr -d ' ')
need=93591101281
reserve=$((100*1024*1024*1024))
if (( free < need + reserve )); then
  state PREFLIGHT FAILED "free=$free need=$need reserve=$reserve"
  exit 10
fi

state DOWNLOAD IN_PROGRESS "free_before=$free selected_remote_bytes=$need"
"$V/bin/python" - "$REPO" "$LOGIC_REV" "$PREFIX" "$DEST" <<'PY'
from huggingface_hub import snapshot_download
import sys
repo,rev,prefix,dest=sys.argv[1:]
p=snapshot_download(
    repo_id=repo,
    revision=rev,
    local_dir=dest,
    allow_patterns=[prefix+'/*','README.md','chat_template.jinja'],
)
print(p)
PY

state VERIFY IN_PROGRESS
"$V/bin/python" - "$DEST" "$PREFIX" "$ROOT/docs/mimo26/evidence/mixed-b3794b22/remote-listing.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
dest=Path(sys.argv[1]); prefix=sys.argv[2]; remote=json.load(open(sys.argv[3]))
var=dest/prefix
assert var.is_dir()
# 1. Remote listing and sizes for selected files.
missing=[]; wrong=[]
for e in remote['files']:
    p=dest/e['path']
    if not p.is_file(): missing.append(e['path']); continue
    if p.stat().st_size!=e['size']: wrong.append((e['path'],e['size'],p.stat().st_size))
if missing or wrong:
    raise SystemExit(f'listing mismatch missing={missing[:20]} wrong={wrong[:20]}')
# 2. SHA256SUMS supplied by release.
expected={}
for line in (var/'SHA256SUMS').read_text().splitlines():
    if not line.strip(): continue
    sha,name=line.split(None,1); expected[name.strip()]=sha
results={}
for name,sha in expected.items():
    p=var/name
    if not p.is_file(): raise SystemExit(f'missing SHA file {name}')
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(16*1024*1024): h.update(b)
    got=h.hexdigest(); results[name]=got
    if got!=sha: raise SystemExit(f'SHA mismatch {name}: {got} != {sha}')
# 3. Artifact manifest large weights.
manifest=json.loads((var/'artifact-manifest.json').read_text())
for e in manifest['weights']:
    if results.get(e['file'])!=e['sha256']:
        raise SystemExit(f'manifest SHA mismatch {e["file"]}')
    if (var/e['file']).stat().st_size!=e['bytes']:
        raise SystemExit(f'manifest size mismatch {e["file"]}')
out={
 'schema':'mimo26-mixed-integrity-v1',
 'status':'COMPLETE',
 'repo_revision':remote['revision'],
 'selected_file_count':len(remote['files']),
 'selected_remote_bytes':remote['total_bytes'],
 'sha256sums_checked':len(results),
 'manifest_weights_checked':len(manifest['weights']),
 'main_weight_bytes':sum(e['bytes'] for e in manifest['weights'] if '0000' in e['file']),
 'all_manifest_weight_bytes':manifest['weight_file_bytes'],
}
(dest/'.mimo26-mixed-verified.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
PY

state COMPLETE COMPLETE
