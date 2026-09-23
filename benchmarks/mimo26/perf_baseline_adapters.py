#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class StreamMeasure:
    t_submit: float
    t_first_token: float | None
    t_last_token: float | None
    t_done: float
    token_ids: list[int]
    text: str
    final_event: dict[str, Any] | None
    empty_events: int
    first_token_event_count: int | None
    complete: bool
    error: str | None

    def normalized(self) -> dict[str, Any]:
        n = len(self.token_ids)
        ttft = None if self.t_first_token is None else self.t_first_token - self.t_submit
        latency = self.t_done - self.t_submit
        post = None
        if (
            n > 1
            and self.t_first_token is not None
            and self.t_last_token is not None
            and self.t_last_token > self.t_first_token
        ):
            post = (n - 1) / (self.t_last_token - self.t_first_token)
        return {
            **asdict(self),
            "output_tokens": n,
            "ttft_observed_s": ttft,
            "request_latency_s": latency,
            "end_to_end_output_rate": n / latency if latency > 0 else None,
            "post_first_token_rate": post,
            "post_first_token_rate_semantics": (
                "APPROX_CHUNKED_FIRST_EVENT"
                if self.first_token_event_count and self.first_token_event_count > 1
                else "TOKEN_EVENT_OBSERVED"
            ) if post is not None else None,
        }


class LlamaStreamCollector:
    def __init__(self, t_submit: float):
        self.t_submit = t_submit
        self.t_first: float | None = None
        self.t_last: float | None = None
        self.tokens: list[int] = []
        self.text_parts: list[str] = []
        self.final: dict[str, Any] | None = None
        self.empty = 0
        self.first_count: int | None = None

    def feed(self, ts: float, event: dict[str, Any]) -> None:
        toks = event.get("tokens") or []
        if toks:
            ids = [int(x) for x in toks]
            if self.t_first is None:
                self.t_first = ts
                self.first_count = len(ids)
            self.t_last = ts
            self.tokens.extend(ids)
        else:
            self.empty += 1

        content = event.get("content")
        if isinstance(content, str) and content:
            self.text_parts.append(content)

        if event.get("stop") is True or "timings" in event:
            self.final = event

    def finish(self, t_done: float, error: str | None = None) -> StreamMeasure:
        return StreamMeasure(
            t_submit=self.t_submit,
            t_first_token=self.t_first,
            t_last_token=self.t_last,
            t_done=t_done,
            token_ids=self.tokens,
            text="".join(self.text_parts),
            final_event=self.final,
            empty_events=self.empty,
            first_token_event_count=self.first_count,
            complete=(error is None and self.final is not None),
            error=error,
        )


def vllm_metrics(output: Any, t_submit: float, t_done: float) -> dict[str, Any]:
    comp = output.outputs[0]
    ids = [int(x) for x in comp.token_ids]
    m = output.metrics

    def g(name: str):
        return getattr(m, name, None) if m is not None else None

    scheduled = g("scheduled_ts")
    first = g("first_token_ts")
    last = g("last_token_ts")
    engine_ttft = (
        float(first - scheduled)
        if first and scheduled and first >= scheduled
        else None
    )
    decode_s = (
        float(last - first)
        if last and first and last >= first
        else None
    )
    engine_post_rate = (
        (len(ids) - 1) / decode_s
        if decode_s and decode_s > 0 and len(ids) > 1
        else None
    )
    latency = t_done - t_submit
    return {
        "t_submit": t_submit,
        "t_first_token_observed": None,
        "t_last_token_observed": None,
        "t_done": t_done,
        "ttft_observed_s": None,
        "request_latency_s": latency,
        "end_to_end_output_rate": len(ids) / latency if latency > 0 else None,
        "output_tokens": len(ids),
        "output_token_ids": ids,
        "text": comp.text,
        "finish_reason": comp.finish_reason,
        "stop_reason": comp.stop_reason,
        "input_token_ids": [int(x) for x in (output.prompt_token_ids or [])],
        "num_cached_tokens": getattr(output, "num_cached_tokens", None),
        "engine": {
            "scheduled_ts": scheduled,
            "first_token_ts": first,
            "last_token_ts": last,
            "time_to_first_token_s": engine_ttft,
            "decode_time_s": decode_s,
            "post_first_token_rate": engine_post_rate,
            "metrics_repr": repr(m),
        },
    }
