#!/usr/bin/env python3
from __future__ import annotations
from types import SimpleNamespace
from perf_baseline_adapters import LlamaStreamCollector, vllm_metrics

# Empty event before output, then a multi-token first event, then one token,
# then terminal timings. This must not mistake the empty progress event for TTFT.
c=LlamaStreamCollector(10.0)
c.feed(10.2,{"content":"","tokens":[],"prompt_progress":{"processed":12}})
c.feed(10.5,{"content":"ab","tokens":[101,102]})
c.feed(10.7,{"content":"c","tokens":[103]})
c.feed(10.8,{"stop":True,"content":"","tokens":[],"timings":{"prompt_n":512}})
r=c.finish(10.81).normalized()
assert r["ttft_observed_s"] == 0.5
assert r["output_tokens"] == 3
assert r["first_token_event_count"] == 2
assert r["post_first_token_rate_semantics"] == "APPROX_CHUNKED_FIRST_EVENT"
assert r["complete"] is True

# Early EOS is complete but short; length classification belongs to the caller.
c=LlamaStreamCollector(20.0)
c.feed(20.4,{"content":"done","tokens":[1,2]})
c.feed(20.41,{"stop":True,"stop_type":"eos","timings":{"predicted_n":2}})
r=c.finish(20.42).normalized()
assert r["complete"] is True and r["output_tokens"] == 2

# Timeout before terminal event remains incomplete and does not fabricate timings.
c=LlamaStreamCollector(30.0)
c.feed(30.5,{"content":"x","tokens":[5]})
r=c.finish(31.0,error="TIMEOUT").normalized()
assert r["complete"] is False and r["error"] == "TIMEOUT"
assert r["post_first_token_rate"] is None

# vLLM extractor uses engine timestamps separately from client wall time.
metrics=SimpleNamespace(scheduled_ts=100.0,first_token_ts=100.5,last_token_ts=101.5)
comp=SimpleNamespace(token_ids=[7,8,9],text="abc",finish_reason="length",stop_reason=None)
out=SimpleNamespace(outputs=[comp],metrics=metrics,prompt_token_ids=[1,2,3],num_cached_tokens=0)
v=vllm_metrics(out,10.0,12.0)
assert v["ttft_observed_s"] is None
assert v["engine"]["time_to_first_token_s"] == 0.5
assert v["engine"]["decode_time_s"] == 1.0
assert v["engine"]["post_first_token_rate"] == 2.0
assert v["num_cached_tokens"] == 0

print("PERF_BASELINE_ADAPTER_SELFTEST_PASS")
