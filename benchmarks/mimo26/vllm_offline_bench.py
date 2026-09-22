#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import os
import re
import socket
import statistics
import time
from pathlib import Path

import torch.distributed as dist
from vllm import LLM, SamplingParams

from vllm_patch import apply_mimo26_vllm_patches

MODEL = os.environ.get(
    "MIMO26_MODEL",
    "/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL",
)
OUT = Path(os.environ.get(
    "MIMO26_RESULT",
    "/home/funboy/.local/state/strixhalomimo26/perf/vllm-result.json",
))
LOAD_OUT = Path(os.environ.get("MIMO26_LOAD_RESULT", str(OUT.with_name("load.json"))))
QUALITY_OUT = Path(os.environ.get("MIMO26_QUALITY_RESULT", str(OUT.with_name("quality.json"))))
TP = int(os.environ.get("MIMO26_TP", "2"))
PP = int(os.environ.get("MIMO26_PP", "1"))
EAGER = os.environ.get("MIMO26_EAGER", "1") == "1"
MAX_LEN = int(os.environ.get("MIMO26_MAX_LEN", "4096"))
KV_BYTES = int(os.environ.get("MIMO26_KV_BYTES", str(1 << 30)))
MAX_BATCHED = int(os.environ.get("MIMO26_MAX_BATCHED", "2048"))
MOE_BACKEND = os.environ.get("MIMO26_MOE_BACKEND", "triton_unfused")
PERF_OUT = int(os.environ.get("MIMO26_OUT_TOKENS", "128"))
REPEATS = int(os.environ.get("MIMO26_REPEATS", "3"))
RUN_PERF = os.environ.get("MIMO26_RUN_PERF", "1") == "1"
PERF_TARGETS = [
    int(x) for x in os.environ.get("MIMO26_PERF_PROMPTS", "512,2048").split(",")
]

rank = int(os.environ.get("RANK", "0"))
world = int(os.environ.get("WORLD_SIZE", "1"))

apply_mimo26_vllm_patches()

kwargs = dict(
    model=MODEL,
    runner="generate",
    trust_remote_code=True,
    language_model_only=True,
    tensor_parallel_size=TP,
    pipeline_parallel_size=PP,
    distributed_executor_backend="external_launcher",
    dtype="bfloat16",
    max_model_len=MAX_LEN,
    max_num_seqs=1,
    max_num_batched_tokens=min(MAX_LEN, MAX_BATCHED),
    kv_cache_memory_bytes=KV_BYTES,
    enforce_eager=EAGER,
    disable_custom_all_reduce=True,
    enable_expert_parallel=False,
    enable_prefix_caching=False,
    seed=1,
    moe_backend=MOE_BACKEND,
)

def atomic_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


if rank == 0:
    atomic_json(LOAD_OUT, {
        "status": "IN_PROGRESS",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    })

t0 = time.perf_counter()
llm = LLM(**kwargs)
load_s = time.perf_counter() - t0
tok = llm.get_tokenizer()

if rank == 0:
    atomic_json(LOAD_OUT, {
        "status": "PASS",
        "load_s": load_s,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tp": TP,
        "pp": PP,
        "moe_backend": MOE_BACKEND,
        "kv_cache_memory_bytes": KV_BYTES,
    })
    atomic_json(QUALITY_OUT, {
        "status": "IN_PROGRESS",
        "tests": [],
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "first_token_observation": "UNAVAILABLE_OFFLINE_LLM_API",
    })


def normalize_ids(value) -> list[int]:
    if hasattr(value, "keys"):
        value = value["input_ids"]
    if hasattr(value, "tolist"):
        value = value.tolist()
    if value and isinstance(value[0], list):
        if len(value) != 1:
            raise ValueError(f"unexpected batched token ids: {len(value)}")
        value = value[0]
    ids = [int(x) for x in value]
    if not ids or min(ids) < 0:
        raise ValueError("invalid token IDs")
    return ids


def chat_ids(text: str) -> list[int]:
    encoded = tok.apply_chat_template(
        [{"role": "user", "content": text}],
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    return normalize_ids(encoded)


def greedy(ids: list[int], max_tokens: int, min_tokens: int = 0, ignore_eos: bool = False):
    p = SamplingParams(
        temperature=0.0,
        seed=1,
        max_tokens=max_tokens,
        min_tokens=min_tokens,
        ignore_eos=ignore_eos,
    )
    start = time.perf_counter()
    # vLLM DecoderOnlyPrompt explicitly accepts list[int].
    # Use the token list directly: r6 showed the generic mapping form could be
    # misinterpreted and reach input validation with string keys.
    out = llm.generate(ids, p, use_tqdm=False)[0]
    wall = time.perf_counter() - start
    c = out.outputs[0]
    return {
        "wall_s": wall,
        "text": c.text,
        "text_stripped": c.text.strip(),
        "token_ids": list(c.token_ids),
        "output_tokens": len(c.token_ids),
        "finish_reason": c.finish_reason,
        "metrics_present": out.metrics is not None,
    }


def extract_code(text: str) -> str:
    m = re.search(r"```(?:python)?\s*(.*?)```", text, flags=re.S | re.I)
    return (m.group(1) if m else text).strip()


def code_gate(text: str) -> tuple[bool, str]:
    code = extract_code(text)
    try:
        tree = ast.parse(code)
    except Exception as e:
        return False, f"parse:{type(e).__name__}:{e}"
    forbidden = (
        ast.Import, ast.ImportFrom, ast.Attribute, ast.With, ast.AsyncWith,
        ast.ClassDef, ast.Lambda, ast.Global, ast.Nonlocal, ast.Delete,
        ast.Try, ast.Raise, ast.While,
    )
    if any(isinstance(n, forbidden) for n in ast.walk(tree)):
        return False, "forbidden_ast"
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(funcs) != 1 or funcs[0].name != "clamp":
        return False, "missing_clamp"
    if any(isinstance(n, ast.Call) for n in ast.walk(tree)):
        return False, "calls_not_allowed"
    ns = {"__builtins__": {}}
    try:
        exec(compile(tree, "<mimo-sanity>", "exec"), ns, ns)
        f = ns["clamp"]
        cases = [
            ((5, 0, 10), 5),
            ((-1, 0, 10), 0),
            ((99, 0, 10), 10),
            ((3, 3, 3), 3),
        ]
        for args, expected in cases:
            got = f(*args)
            if got != expected:
                return False, f"unit_fail:{args}:{got}!={expected}"
    except Exception as e:
        return False, f"exec:{type(e).__name__}:{e}"
    return True, "PASS"


sanity_specs = [
    ("arithmetic", "Compute 17*19. Return only the integer.", lambda s: s == "323"),
    ("extract", "Read this exact token: ZEBRA-4821. Return only that token.", lambda s: s == "ZEBRA-4821"),
    (
        "json",
        'Return only valid JSON with exactly these values: alpha is integer 7 and beta is string "blue".',
        lambda s: (lambda o: isinstance(o, dict) and o == {"alpha": 7, "beta": "blue"})(json.loads(s)),
    ),
    (
        "italian",
        "Nel testo seguente il colore dichiarato è cobalto. Rispondi solo con il nome del colore.",
        lambda s: s.casefold() == "cobalto",
    ),
    ("english", "Alice is first and Bob is second. Who is second? Return only the name.", lambda s: s == "Bob"),
]

sanity = []
for name, prompt, check in sanity_specs:
    ids = chat_ids(prompt)
    r = greedy(ids, 64)
    try:
        ok = bool(check(r["text_stripped"]))
        reason = "PASS" if ok else "expected_mismatch"
    except Exception as e:
        ok = False
        reason = f"check:{type(e).__name__}:{e}"
    sanity.append({
        "name": name,
        "prompt": prompt,
        "prompt_token_ids": ids,
        "prompt_tokens": len(ids),
        "pass": ok,
        "reason": reason,
        **r,
    })
    if rank == 0:
        atomic_json(QUALITY_OUT, {
            "status": "IN_PROGRESS",
            "tests": sanity,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "first_token_observation": "UNAVAILABLE_OFFLINE_LLM_API",
        })

code_prompt = (
    "Return only Python code defining clamp(x, lo, hi). "
    "It must return lo when x < lo, hi when x > hi, otherwise x. "
    "Do not import anything and do not call other functions."
)
code_ids = chat_ids(code_prompt)
code_result = greedy(code_ids, 96)
code_ok, code_reason = code_gate(code_result["text_stripped"])
sanity.append({
    "name": "code_clamp",
    "prompt": code_prompt,
    "prompt_token_ids": code_ids,
    "prompt_tokens": len(code_ids),
    "pass": code_ok,
    "reason": code_reason,
    **code_result,
})

quality_pass = all(x["pass"] for x in sanity)
if rank == 0:
    atomic_json(QUALITY_OUT, {
        "status": "PASS" if quality_pass else "FAIL",
        "tests": sanity,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "first_token_observation": "UNAVAILABLE_OFFLINE_LLM_API",
        "thinking": False,
    })

result = {
    "schema": "mimo26-vllm-correctness-perf-v1",
    "rank": rank,
    "world": world,
    "hostname": socket.gethostname(),
    "config": {
        "tp": TP,
        "pp": PP,
        "eager": EAGER,
        "max_model_len": MAX_LEN,
        "kv_cache_memory_bytes": KV_BYTES,
        "max_num_batched_tokens": MAX_BATCHED,
        "moe_backend": MOE_BACKEND,
        "prefix_caching": False,
        "language_model_only": True,
        "thinking": False,
        "run_performance": RUN_PERF,
    },
    "load_s": load_s,
    "sanity": sanity,
    "quality_pass": quality_pass,
    "performance": [],
}

if quality_pass and RUN_PERF:
    base = (
        "Explain a deterministic Python implementation of a bounded ring buffer. "
        "State invariants, time and space complexity, edge cases, and include a compact "
        "correct code example. Be precise and avoid repetition. "
    )
    for target in PERF_TARGETS:
        user = base
        ids = chat_ids(user)
        while len(ids) < target:
            user += base
            ids = chat_ids(user)
        prompt_tokens = len(ids)

        greedy(ids, 8, min_tokens=8, ignore_eos=True)

        reps = []
        for rep in range(REPEATS):
            one = greedy(ids, 1, min_tokens=1, ignore_eos=True)
            full = greedy(ids, PERF_OUT, min_tokens=PERF_OUT, ignore_eos=True)
            decode_s = max(0.0, full["wall_s"] - one["wall_s"])
            reps.append({
                "rep": rep + 1,
                "prompt_tokens": prompt_tokens,
                "one_token_wall_s": one["wall_s"],
                "prefill_est_tps": prompt_tokens / one["wall_s"],
                "output_tokens": full["output_tokens"],
                "full_wall_s": full["wall_s"],
                "wall_output_tps": full["output_tokens"] / full["wall_s"],
                "decode_est_s": decode_s,
                "decode_est_tps": (
                    (full["output_tokens"] - 1) / decode_s
                    if decode_s > 0 and full["output_tokens"] > 1 else None
                ),
                "finish_reason": full["finish_reason"],
                "text_prefix": full["text"][:500],
                "token_ids_prefix": full["token_ids"][:32],
                "timing_kind": "estimated_by_1_token_subtraction",
            })
        valid_decode = [r["decode_est_tps"] for r in reps if r["decode_est_tps"] is not None]
        result["performance"].append({
            "target_prompt_tokens": target,
            "actual_prompt_tokens": prompt_tokens,
            "repeats": reps,
            "summary": {
                "decode_est_tps_median": statistics.median(valid_decode),
                "decode_est_tps_min": min(valid_decode),
                "decode_est_tps_max": max(valid_decode),
                "prefill_est_tps_median": statistics.median(r["prefill_est_tps"] for r in reps),
                "wall_output_tps_median": statistics.median(r["wall_output_tps"] for r in reps),
            },
        })

print("MIMO26_RESULT " + json.dumps(result, ensure_ascii=False), flush=True)
if rank == 0:
    atomic_json(OUT, result)

if dist.is_initialized():
    dist.barrier()

if not quality_pass:
    raise SystemExit(40)
