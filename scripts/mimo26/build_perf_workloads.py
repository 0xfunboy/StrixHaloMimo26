#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from transformers import AutoTokenizer

MODEL = "/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL"
OUT = Path("/home/funboy/StrixHaloMimo26/docs/mimo26/perf-baseline-001/workloads.json")

tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True, local_files_only=True)

intro = (
    "You are reviewing a production design for a deterministic bounded event-processing service. "
    "Write a rigorous technical audit that is longer than 128 output tokens. "
    "Explain invariants, failure modes, concurrency behavior, observability, recovery, and concrete validation steps. "
    "Do not merely restate the specification; identify interactions between requirements and propose precise checks.\n\n"
)

subjects = [
    "ring buffer", "sequence allocator", "producer path", "consumer path", "checkpoint writer",
    "recovery journal", "metrics collector", "backpressure controller", "ownership table",
    "timestamp recorder", "batch scheduler", "network ingress", "persistent manifest",
    "validation harness", "shutdown protocol", "memory allocator", "retry controller",
    "request ledger", "cache policy", "fault monitor",
]
properties = [
    "must preserve monotonic sequence numbers across wraparound",
    "must reject stale ownership epochs before mutating shared state",
    "must bound memory independently of request arrival rate",
    "must record a durable cause before cleanup can overwrite transient state",
    "must separate queueing time from execution time in every latency metric",
    "must expose exact processed and reused token counters rather than infer them",
    "must make retries idempotent under coordinator interruption",
    "must keep validation output atomic even if teardown is interrupted",
    "must prevent a warm kernel from implying reuse of prior request state",
    "must make partial completion visible instead of silently excluding the sample",
    "must isolate correctness gates from throughput measurements",
    "must preserve deterministic sampling parameters across repeated measurements",
    "must distinguish process memory, file-backed mappings, and shared device memory",
    "must avoid global state changes when a per-run setting is sufficient",
    "must leave enough evidence to reconstruct the first failing event",
    "must verify worker termination before releasing exclusive ownership",
    "must treat a successful restore as independent from the workload outcome",
    "must retain raw counters before computing derived rates",
    "must use monotonic clocks for request intervals",
    "must validate exact input identity before comparing runtimes",
]
conditions = [
    "after a producer crash during wraparound",
    "when two workers race to observe a timeout",
    "after a coordinator receives SIGTERM",
    "when a request reaches the output-token limit",
    "when the downstream consumer is temporarily unavailable",
    "after a cold restart with an existing journal",
    "when the queue is full and backpressure is active",
    "when a checkpoint lands between two state transitions",
    "when a retry sees a completed but unacknowledged operation",
    "while metrics are sampled under load",
    "when the same prompt text is submitted repeatedly",
    "when a worker exits before persisting quality results",
    "when cleanup itself exceeds its budget",
    "while one node is slower than its peer",
    "when a mapped model file incurs major faults",
    "while the system is thermally stable but clocks vary",
    "when an EOS token appears before the requested budget",
    "when a request contains exactly the context boundary",
    "when a runtime reports cached input tokens",
    "when an adapter emits an empty streaming event",
]

sentences = []
for i in range(1, 260):
    s = subjects[(i - 1) % len(subjects)]
    p = properties[(i * 7 - 3) % len(properties)]
    c = conditions[(i * 11 - 5) % len(conditions)]
    sentences.append(f"Requirement {i}: the {s} {p} {c}.")

tech_words = [
    "state", "buffer", "index", "queue", "ring", "capacity", "invariant", "pointer", "offset", "atomic",
    "lock", "thread", "memory", "token", "prompt", "decode", "latency", "metric", "cache", "kernel",
    "tensor", "expert", "shard", "scale", "runtime", "stream", "event", "output", "input", "model",
    "node", "device", "network", "socket", "clock", "power", "thermal", "batch", "context", "request",
    "response", "journal", "epoch", "owner", "retry", "timeout", "cleanup", "restore", "worker", "scheduler",
    "sequence", "checkpoint", "manifest", "validation", "throughput", "prefill", "sampling", "deterministic",
    "failure", "recovery", "bounded", "concurrency", "observability", "backpressure", "producer", "consumer",
    "progress", "timestamp", "payload", "completion", "prefix", "reuse", "counter", "evidence", "integrity",
]

def ids_for(content: str):
    msgs = [{"role": "user", "content": content}]
    ids = tok.apply_chat_template(
        msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False
    )
    if hasattr(ids, "keys"):
        ids = ids["input_ids"]
    if hasattr(ids, "tolist"):
        ids = ids.tolist()
    if ids and isinstance(ids[0], list):
        ids = ids[0]
    rendered = tok.apply_chat_template(
        msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    return [int(x) for x in ids], rendered

def make(target: int):
    content = intro
    for sentence in sentences:
        trial = content + sentence + "\n"
        n = len(ids_for(trial)[0])
        if n > target - 70:
            break
        content = trial

    content += "\nAudit checklist keywords:"
    ids, rendered = ids_for(content)
    wi = 0
    while len(ids) < target:
        remaining = target - len(ids)
        found = False
        for j in range(len(tech_words)):
            word = tech_words[(wi + j) % len(tech_words)]
            trial = content + " " + word
            t_ids, t_rendered = ids_for(trial)
            delta = len(t_ids) - len(ids)
            if 0 < delta <= remaining:
                content = trial
                ids = t_ids
                rendered = t_rendered
                wi = (wi + j + 1) % len(tech_words)
                found = True
                break
        if not found:
            for frag in [";", " audit", " verify", " bound", " exact", " stable", " safe", " log", " id", " rate"]:
                trial = content + frag
                t_ids, t_rendered = ids_for(trial)
                if len(t_ids) == target:
                    content = trial
                    ids = t_ids
                    rendered = t_rendered
                    found = True
                    break
        if not found:
            raise RuntimeError(f"cannot close token gap target={target} current={len(ids)}")

    assert len(ids) == target
    rendered_ids = tok.encode(rendered, add_special_tokens=False)
    assert list(rendered_ids) == ids, (target, len(rendered_ids), len(ids))
    return {
        "target_input_tokens": target,
        "messages": [{"role": "user", "content": content}],
        "rendered_text": rendered,
        "rendered_text_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
        "input_token_ids": ids,
        "input_token_ids_sha256": hashlib.sha256(
            json.dumps(ids, separators=(",", ":")).encode()
        ).hexdigest(),
        "input_tokens": len(ids),
        "thinking": False,
        "add_generation_prompt": True,
    }

workloads = {str(n): make(n) for n in (512, 2048)}
out = {
    "schema": "mimo26-perf-baseline-workloads-v1",
    "tokenizer_source": MODEL,
    "tokenizer_json_sha256": hashlib.sha256((Path(MODEL) / "tokenizer.json").read_bytes()).hexdigest(),
    "chat_template_sha256": hashlib.sha256((Path(MODEL) / "chat_template.jinja").read_bytes()).hexdigest(),
    "sampling": {
        "temperature": 0.0,
        "seed": 1,
        "max_output_tokens": 128,
        "thinking": False,
        "prefix_prompt_reuse": False,
    },
    "request_order": [512, 2048, 2048, 512, 512, 2048],
    "warmup_order": [512, 2048],
    "workloads": workloads,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({
    "tokenizer_json_sha256": out["tokenizer_json_sha256"],
    "chat_template_sha256": out["chat_template_sha256"],
    "workloads": {
        k: {
            "input_tokens": v["input_tokens"],
            "rendered_text_sha256": v["rendered_text_sha256"],
            "token_ids_sha256": v["input_token_ids_sha256"],
            "source_chars": len(v["messages"][0]["content"]),
        }
        for k, v in workloads.items()
    },
}, indent=2))
