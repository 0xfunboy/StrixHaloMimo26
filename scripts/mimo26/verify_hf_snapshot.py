#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path

from huggingface_hub import HfApi


def human_gib(n: int) -> str:
    return f"{n / (1024 ** 3):.3f} GiB"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(16 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def atomic_json(path: Path, obj: object) -> None:
    atomic_text(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--revision", required=True)
    ap.add_argument("--local-dir", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--manifest-md", required=True)
    ap.add_argument("--sha-manifest", required=True)
    ap.add_argument("--files-manifest", required=True)
    args = ap.parse_args()

    root = Path(args.local_dir).resolve()
    if not root.is_dir():
        raise SystemExit(f"local dir missing: {root}")

    incompletes = sorted(str(p) for p in root.rglob("*.incomplete"))
    if incompletes:
        print(json.dumps({"status": "FAIL", "reason": "incomplete_files", "files": incompletes}, indent=2))
        return 2

    api = HfApi()
    info = api.model_info(args.repo, revision=args.revision, files_metadata=True)
    expected: dict[str, int] = {}
    lfs_sha: dict[str, str] = {}
    for s in info.siblings:
        expected[s.rfilename] = int(s.size or 0)
        lfs = getattr(s, "lfs", None)
        if lfs is not None:
            sha = getattr(lfs, "sha256", None)
            if sha:
                lfs_sha[s.rfilename] = sha

    local: dict[str, int] = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith(".cache/") or rel == ".mimo26-verified.json":
            continue
        local[rel] = p.stat().st_size

    missing = sorted(set(expected) - set(local))
    extra = sorted(set(local) - set(expected))
    wrong_size = sorted(
        [{"path": name, "expected": expected[name], "actual": local[name]}
         for name in set(expected) & set(local)
         if expected[name] != local[name]],
        key=lambda x: x["path"],
    )

    if missing or extra or wrong_size:
        print(json.dumps({
            "status": "FAIL",
            "reason": "listing_or_size_mismatch",
            "missing": missing,
            "extra": extra,
            "wrong_size": wrong_size,
        }, indent=2))
        return 3

    file_lines = ["size_bytes\tpath"]
    for name in sorted(expected):
        file_lines.append(f"{expected[name]}\t{name}")
    atomic_text(Path(args.files_manifest), "\n".join(file_lines) + "\n")

    sha_lines: list[str] = []
    upstream_sha_matches = 0
    upstream_sha_mismatches: list[str] = []
    for idx, name in enumerate(sorted(expected), start=1):
        p = root / name
        digest = sha256_file(p)
        sha_lines.append(f"{digest}  {name}")
        if name in lfs_sha:
            if digest == lfs_sha[name]:
                upstream_sha_matches += 1
            else:
                upstream_sha_mismatches.append(name)
        print(json.dumps({
            "event": "sha256",
            "index": idx,
            "count": len(expected),
            "path": name,
            "size": expected[name],
            "sha256": digest,
        }), flush=True)

    if upstream_sha_mismatches:
        print(json.dumps({
            "status": "FAIL",
            "reason": "upstream_lfs_sha_mismatch",
            "files": upstream_sha_mismatches,
        }, indent=2))
        return 4

    atomic_text(Path(args.sha_manifest), "\n".join(sha_lines) + "\n")

    total = sum(expected.values())
    safetensors = [x for x in sorted(expected) if x.lower().endswith(".safetensors")]
    ggufs = [x for x in sorted(expected) if x.lower().endswith(".gguf")]
    aux_rx = re.compile(r"(config|tokenizer|processor|preprocessor|template|chat|vision|image|video|projector|mtp|dflash)", re.I)
    aux = [x for x in sorted(expected) if aux_rx.search(x) and not x.lower().endswith((".safetensors", ".gguf"))]

    md = [
        f"# {args.label} manifest",
        "",
        f"- Repository: `{args.repo}`",
        f"- Requested revision: `{args.revision}`",
        f"- Resolved revision: `{info.sha}`",
        f"- Local directory: `{root}`",
        f"- Files: {len(expected)}",
        f"- Total: {total} bytes ({human_gib(total)})",
        f"- Safetensors: {len(safetensors)}",
        f"- GGUF: {len(ggufs)}",
        f"- Upstream LFS SHA256 matches checked: {upstream_sha_matches}",
        "- Listing/size comparison: PASS",
        "- Local SHA256 manifest: complete",
        "- .incomplete files: 0",
        "",
        "## Runtime / config / tokenizer / multimodal files",
        "",
    ]
    md.extend(f"- `{x}`" for x in aux)
    md += ["", "## Weight files", ""]
    md.extend(f"- `{x}` — {expected[x]} bytes" for x in safetensors + ggufs)
    md += ["", "## Verification", "", "STATUS: **COMPLETE**", ""]
    atomic_text(Path(args.manifest_md), "\n".join(md))

    marker = {
        "schema": "mimo26-hf-snapshot-verification-v1",
        "repo": args.repo,
        "requested_revision": args.revision,
        "resolved_revision": info.sha,
        "local_dir": str(root),
        "file_count": len(expected),
        "total_bytes": total,
        "safetensors": len(safetensors),
        "gguf": len(ggufs),
        "sha_manifest": str(Path(args.sha_manifest).resolve()),
        "files_manifest": str(Path(args.files_manifest).resolve()),
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": "COMPLETE",
    }
    atomic_json(root / ".mimo26-verified.json", marker)
    print(json.dumps(marker, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
