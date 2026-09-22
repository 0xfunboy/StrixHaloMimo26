#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

ROOT=Path("/home/funboy/StrixHaloMimo26")
STATE=Path("/home/funboy/.local/state/strixhalomimo26/mixed-download")
DEST=Path("/home/funboy/models/MiMo-V2.6/mixed-gguf/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF")
VAR=DEST/"MQ-IQ2-XXS-XS-Q8-MM-BF16"
EVID=ROOT/"docs/mimo26/evidence/mixed-b3794b22"
REPO="Baekpica/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF"
REV="b3794b22b6276f8120c340f52639f5eaa354a3fd"
MANIFEST=json.loads((EVID/"MQ-IQ2-XXS-XS-Q8-MM-BF16__artifact-manifest.json").read_text())

STATE.mkdir(parents=True,exist_ok=True)
VAR.mkdir(parents=True,exist_ok=True)
lock=(STATE/"download.lock").open("w")
try:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit("mixed download already running")

def atomic(path:Path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    q=path.with_suffix(path.suffix+".tmp")
    q.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
    os.replace(q,path)

def sha256(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(16*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def seed_from_hf_cache(expected_sha: str, expected_size: int, part: Path):
    """Reuse the largest HF/Xet partial for the exact LFS object.

    The cache filename embeds the authoritative LFS SHA256.  This is only a
    bandwidth optimization: the prefix is never trusted as complete.  The
    finished file must still match exact size and full manifest SHA256 before
    atomic rename.
    """
    cache=DEST/".cache/huggingface/download/MQ-IQ2-XXS-XS-Q8-MM-BF16"
    candidates=[]
    if cache.is_dir():
        for p in cache.glob(f"*.{expected_sha}.*.incomplete"):
            try:
                n=p.stat().st_size
            except FileNotFoundError:
                continue
            if 0 < n < expected_size:
                candidates.append((n,p))
    if not candidates:
        return None
    n,p=max(candidates,key=lambda x:x[0])
    current=part.stat().st_size if part.exists() else 0
    if n <= current:
        return None
    # GGUF shard/projector/draft files must at least have the GGUF magic.
    with p.open("rb") as f:
        magic=f.read(4)
    if magic != b"GGUF":
        return {"status":"REJECTED_BAD_MAGIC","source":str(p),"bytes":n}
    tmp=part.with_suffix(part.suffix+".seedtmp")
    subprocess.run(
        ["cp","--reflink=auto","--sparse=always",str(p),str(tmp)],
        check=True,
    )
    os.replace(tmp,part)
    return {
        "status":"SEEDED_UNVERIFIED_PREFIX",
        "source":str(p),
        "bytes":n,
        "previous_part_bytes":current,
    }

state={
    "schema":"mimo26-mixed-download-v1",
    "repo":REPO,"revision":REV,"status":"IN_PROGRESS",
    "started_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "files":{},
}
atomic(STATE/"state.json",state)

for item in MANIFEST["weights"]:
    name=item["file"]; size=int(item["bytes"]); expected=item["sha256"]
    dst=VAR/name; part=VAR/(name+".part")
    rec=state["files"].setdefault(name,{})
    rec.update({"expected_bytes":size,"expected_sha256":expected})
    if dst.exists() and dst.stat().st_size==size:
        got=sha256(dst)
        if got==expected:
            rec.update({"status":"COMPLETE","bytes":size,"sha256":got})
            atomic(STATE/"state.json",state)
            continue
        rec.update({"status":"BAD_FINAL_HASH","actual_sha256":got})
        atomic(STATE/"state.json",state)
        raise SystemExit(f"bad existing final hash: {name}")
    if dst.exists():
        rec.update({"status":"BAD_FINAL_SIZE","actual_bytes":dst.stat().st_size})
        atomic(STATE/"state.json",state)
        raise SystemExit(f"bad existing final size: {name}")

    seed=seed_from_hf_cache(expected,size,part)
    if seed is not None:
        rec["hf_cache_seed"]=seed
        atomic(STATE/"state.json",state)

    url=(
        "https://huggingface.co/"
        + REPO
        + "/resolve/"
        + REV
        + "/MQ-IQ2-XXS-XS-Q8-MM-BF16/"
        + quote(name)
        + "?download=true"
    )
    rec.update({"status":"DOWNLOADING","part":str(part),"url":url})
    atomic(STATE/"state.json",state)
    cmd=[
        "curl","-L","--fail","--retry","30","--retry-all-errors",
        "--connect-timeout","30","--speed-time","120","--speed-limit","1048576",
        "-C","-","-o",str(part),url,
    ]
    subprocess.run(cmd,check=True)
    if part.stat().st_size!=size:
        rec.update({"status":"SIZE_MISMATCH","actual_bytes":part.stat().st_size})
        atomic(STATE/"state.json",state)
        raise SystemExit(f"size mismatch for {name}")
    got=sha256(part)
    if got!=expected:
        rec.update({"status":"HASH_MISMATCH","actual_sha256":got})
        atomic(STATE/"state.json",state)
        raise SystemExit(f"sha mismatch for {name}")
    os.replace(part,dst)
    rec.update({"status":"COMPLETE","bytes":size,"sha256":got,"finished_at":time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    atomic(STATE/"state.json",state)

# Copy already-downloaded authoritative sidecars into evidence if present.
for srcname,dstname in [
    ("SHA256SUMS","SHA256SUMS"),
    ("artifact-manifest.json","artifact-manifest.json"),
    ("quant-recipe.json","quant-recipe.json"),
    ("toolchain-pins.json","toolchain-pins.json"),
    ("quality-status.json","quality-status.json"),
    ("tensor-types.txt","tensor-types.txt"),
]:
    src=VAR/srcname
    if src.exists():
        (EVID/dstname).write_bytes(src.read_bytes())

verified={
    "schema":"mimo26-mixed-verified-v1",
    "repo":REPO,"revision":REV,
    "variant":"MQ-IQ2-XXS-XS-Q8-MM-BF16",
    "status":"INTEGRITY_VERIFIED_RUNTIME_NOT_YET_VALIDATED",
    "verified_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "weight_file_bytes":sum(int(x["bytes"]) for x in MANIFEST["weights"]),
    "main_tensor_payload_bytes":MANIFEST["main_tensor_payload_bytes"],
    "files":state["files"],
}
atomic(VAR/".mixed-verified.json",verified)
state["status"]="COMPLETE"
state["finished_at"]=verified["verified_at"]
atomic(STATE/"state.json",state)
print(json.dumps(verified,indent=2))
