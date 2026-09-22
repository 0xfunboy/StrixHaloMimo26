#!/usr/bin/env python3
from __future__ import annotations
import json, os, socket, time
import torch
import torch.distributed as dist

backend = os.environ.get("MIMO26_PROBE_BACKEND", "gloo")
rank = int(os.environ["RANK"])
world = int(os.environ["WORLD_SIZE"])
local_rank = int(os.environ.get("LOCAL_RANK", "0"))
started = time.perf_counter()

if backend == "nccl":
    torch.cuda.set_device(local_rank)
    device = torch.device("cuda", local_rank)
else:
    device = torch.device("cpu")

dist.init_process_group(backend=backend, init_method="env://")
x = torch.tensor([float(rank + 1)], device=device)
dist.all_reduce(x, op=dist.ReduceOp.SUM)
if device.type == "cuda":
    torch.cuda.synchronize()
elapsed = time.perf_counter() - started
out = {
    "rank": rank,
    "world": world,
    "hostname": socket.gethostname(),
    "backend": backend,
    "device": str(device),
    "sum": float(x.cpu().item()),
    "elapsed_s": elapsed,
}
print(json.dumps(out), flush=True)
assert abs(out["sum"] - world * (world + 1) / 2) < 1e-6
dist.barrier()
dist.destroy_process_group()
