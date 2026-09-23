#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StreamMeasure:
    target_output_tokens: int
    t_submit: float
    t_first_token: float | None = None
    t_last_token: float | None = None
    t_done: float | None = None
    token_ids: list[int] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    finish_reason: str | None = None
    complete: bool = False
    first_event_token_count: int | None = None
    empty_events: int = 0
    native_final: dict[str, Any] | None = None
    prompt_progress: list[dict[str, Any]] = field(default_factory=list)

    def feed(self, event: dict[str, Any], now: float) -> None:
        if "prompt_progress" in event:
            # This llama.cpp build emits placeholder token id 0 on prompt
            # progress chunks. They are not generated output tokens and must
            # not define TTFT or contribute to output token counts.
            self.prompt_progress.append(event["prompt_progress"])
            return

        tokens = event.get("tokens") or []
        content = event.get("content")
        if tokens:
            ids = [int(x) for x in tokens]
            if self.t_first_token is None:
                self.t_first_token = now
                self.first_event_token_count = len(ids)
            self.t_last_token = now
            self.token_ids.extend(ids)
        elif content:
            # A non-empty content event without token ids is observable output,
            # but token-based rate cannot be exact. Record the first timestamp.
            if self.t_first_token is None:
                self.t_first_token = now
                self.first_event_token_count = 0
            self.t_last_token = now
        else:
            self.empty_events += 1

        if content:
            self.text_parts.append(str(content))

        # llama.cpp native /completion uses stop=true on terminal event.
        if event.get("stop") is True or event.get("final") is True:
            self.complete = True
            self.t_done = now
            self.finish_reason = (
                event.get("stop_type")
                or event.get("finish_reason")
                or event.get("stop_reason")
            )
            self.native_final = event

    def timeout(self, now: float) -> None:
        if self.t_done is None:
            self.t_done = now
        self.complete = False
        if self.finish_reason is None:
            self.finish_reason = "timeout"

    def finalize(self) -> dict[str, Any]:
        n = len(self.token_ids)
        request_latency = (
            self.t_done - self.t_submit if self.t_done is not None else None
        )
        ttft = (
            self.t_first_token - self.t_submit
            if self.t_first_token is not None
            else None
        )
        post = None
        if (
            n > 1
            and self.t_first_token is not None
            and self.t_last_token is not None
            and self.t_last_token > self.t_first_token
        ):
            post = (n - 1) / (self.t_last_token - self.t_first_token)

        if not self.complete:
            status = "INCOMPLETE"
        elif n < self.target_output_tokens:
            status = "SHORT_OUTPUT"
        elif n == self.target_output_tokens:
            status = "VALID_128"
        else:
            status = "OVER_OUTPUT"

        return {
            "status": status,
            "complete": self.complete,
            "output_tokens": n,
            "output_token_ids": self.token_ids,
            "text": "".join(self.text_parts),
            "finish_reason": self.finish_reason,
            "t_submit": self.t_submit,
            "t_first_token": self.t_first_token,
            "t_last_token": self.t_last_token,
            "t_done": self.t_done,
            "ttft_observed_s": ttft,
            "post_first_token_rate_tps": post,
            "request_latency_s": request_latency,
            "end_to_end_output_rate_tps": (
                n / request_latency if request_latency and request_latency > 0 else None
            ),
            "first_event_token_count": self.first_event_token_count,
            "first_event_multi_token": (
                self.first_event_token_count is not None
                and self.first_event_token_count > 1
            ),
            "empty_events": self.empty_events,
            "prompt_progress": self.prompt_progress,
            "native_final": self.native_final,
        }


def vllm_metrics_to_dict(metrics: Any) -> dict[str, Any] | None:
    if metrics is None:
        return None
    fields = [
        "num_generation_tokens",
        "arrival_time",
        "queued_ts",
        "scheduled_ts",
        "first_token_ts",
        "last_token_ts",
        "first_token_latency",
        "is_corrupted",
    ]
    out = {k: getattr(metrics, k, None) for k in fields}
    ft = out.get("first_token_ts")
    lt = out.get("last_token_ts")
    n = out.get("num_generation_tokens") or 0
    out["engine_post_first_token_rate_tps"] = (
        (n - 1) / (lt - ft)
        if n > 1 and ft and lt and lt > ft
        else None
    )
    out["engine_scheduled_to_first_token_s"] = (
        ft - out["scheduled_ts"]
        if ft and out.get("scheduled_ts") and ft >= out["scheduled_ts"]
        else None
    )
    return out


def classify_output(
    output_tokens: int,
    target_output_tokens: int,
    finish_reason: str | None,
    complete: bool = True,
) -> str:
    if not complete:
        return "INCOMPLETE"
    if output_tokens < target_output_tokens:
        return "SHORT_OUTPUT"
    if output_tokens == target_output_tokens:
        return "VALID_128"
    return "OVER_OUTPUT"


def read_meminfo_bytes() -> dict[str, int]:
    out: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" not in line:
            continue
        k, raw = line.split(":", 1)
        parts = raw.strip().split()
        if not parts:
            continue
        value = int(parts[0])
        if len(parts) > 1 and parts[1] == "kB":
            value *= 1024
        out[k] = value
    return out


def read_proc_snapshot(pid: int | None = None) -> dict[str, Any]:
    pid = pid or os.getpid()
    out: dict[str, Any] = {"pid": pid}
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith(("VmRSS:", "VmSize:", "VmSwap:", "RssAnon:", "RssFile:")):
                k, raw = line.split(":", 1)
                n, unit = raw.strip().split()[:2]
                out[k] = int(n) * (1024 if unit == "kB" else 1)
        stat = Path(f"/proc/{pid}/stat").read_text().split()
        out["minflt"] = int(stat[9])
        out["majflt"] = int(stat[11])
        io = {}
        for line in Path(f"/proc/{pid}/io").read_text().splitlines():
            k, v = line.split(":", 1)
            io[k] = int(v.strip())
        out["io"] = io
    except (FileNotFoundError, ProcessLookupError):
        out["exited"] = True
    return out


def amd_smi_snapshot() -> dict[str, Any] | None:
    exe = os.environ.get("MIMO26_AMD_SMI")
    if not exe:
        return None
    try:
        cp = subprocess.run(
            [exe, "metric", "-p", "-c", "-t", "-m", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if cp.returncode != 0:
            return {"error": cp.stderr.strip(), "returncode": cp.returncode}
        return json.loads(cp.stdout)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def system_snapshot(pid: int | None = None) -> dict[str, Any]:
    m = read_meminfo_bytes()
    return {
        "mem": {
            k: m.get(k)
            for k in ("MemTotal", "MemAvailable", "MemFree", "SwapTotal", "SwapFree", "Cached")
        },
        "process": read_proc_snapshot(pid),
        "amd_smi": amd_smi_snapshot(),
    }


def append_jsonl(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def atomic_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    q = p.with_suffix(p.suffix + ".tmp")
    q.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    os.replace(q, p)


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)
