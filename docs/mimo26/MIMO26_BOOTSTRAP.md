# StrixHaloMimo26 bootstrap

Bootstrap started: **2026-09-22**.

## Provenance

- DS41 source working repository: `/home/funboy/StrixHaloClusterDS41`
- DS41 source commit: `a52b867f1b285c6a660ea182f297e4ad271c898c`
- DS41 source branch at bootstrap: `exp/ds41-q2-001`
- DS41 historical GitHub remote: `https://github.com/0xfunboy/StrixHaloClusterDS41.git`
- Source working tree at bootstrap: **dirty with 35 untracked entries; left untouched**
- Note: the local DS41 `exp/ds41-q2-001` HEAD differed from the then-current GitHub tracking ref. MiMo is intentionally based on the local source HEAD above.
- Local MiMo repository: `/home/funboy/StrixHaloMimo26`
- New remote: `https://github.com/0xfunboy/StrixHaloMimo26.git`
- Working branch: `mimo26/main`
- Clone method: `git clone --no-hardlinks`; sample inode check found no shared loose-object inode.

## Hardware target

- NODE01: `01-EVO-X3`
- NODE02: `02-EVO-X3`
- Hardware scope: **two Strix Halo only**
- RTX 3090 / CUDA: **not used**
- DS41 resident services: preserved; E1 was READY during bootstrap.

## Model targets

### Model 1 — official

- Repository: `XiaomiMiMo/MiMo-V2.6-Flash-RL`
- Pinned HF revision: `5711b268169967567844e1e560e8a3966da959b1`
- Local directory: `/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL`
- Status: **COMPLETE**
- Upstream metadata at preflight: 90 files, 177767644228 bytes (~165.559 GiB)

### Model 2 — mixed GGUF

- Repository: `Baekpica/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF`
- Local directory: `/home/funboy/models/MiMo-V2.6/mixed-gguf/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF`
- Status: **WAITING_UPSTREAM**
- Gate checked after Model 1 verification: revision f6af40169a5e4624821773ef4486a5beec4d1da8, GGUF files: 0.

## Storage / tooling

- Disk free before model downloads: 516557967360 bytes (~481 GiB)
- Dedicated Hugging Face venv: `/home/funboy/.local/share/strixhalomimo26/hf-venv`
- Downloader: official `hf download`, with public access and resume support.
- Sequential runner: `scripts/mimo26/download-sequential.sh`
- Runtime registry: `/home/funboy/.local/state/strixhalomimo26/download-state.json`

## Isolation

Weights live outside Git. The repository contains only code, docs, manifests and provenance. DS41 remains the historical baseline and is not modified by this bootstrap.

No conversion, deploy, benchmark, CUDA setup, kernel/ROCm/network/USB4 change, or model distribution to NODE02 is part of this task.

## Terminal bootstrap state

- Model 1 verified: 2026-09-22T08:56:48+0200
- Model 1 files: 90
- Model 1 total bytes: 177767644228
- Model 1 safetensors: 67
- Model 1 SHA256 manifest: docs/mimo26/manifests/mimo26-official.sha256
- Model 2 gate revision: f6af40169a5e4624821773ef4486a5beec4d1da8
- Model 2 GGUF count: 0
- Model 2 status: **WAITING_UPSTREAM**
- Disk free after Model 1: 338769039360 bytes
