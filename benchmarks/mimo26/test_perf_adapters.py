#!/usr/bin/env python3
from __future__ import annotations

from perf_measure_common import StreamMeasure, classify_output


def test_empty_then_tokens():
    m=StreamMeasure(3,10.0)
    m.feed({},10.1)
    m.feed({"content":"","tokens":[]},10.2)
    # Real llama.cpp progress chunks in this build may include placeholder
    # token id 0; these must not count as generated output or TTFT.
    m.feed({"content":"","tokens":[0],"prompt_progress":{"cache":0,"processed":128,"total":512}},10.3)
    m.feed({"content":"a","tokens":[1]},10.5)
    m.feed({"content":"bc","tokens":[2,3]},10.7)
    m.feed({"stop":True,"stop_type":"limit","content":"","tokens":[]},10.8)
    r=m.finalize()
    assert r["output_token_ids"]==[1,2,3]
    assert r["ttft_observed_s"]==0.5
    assert r["first_event_multi_token"] is False
    assert r["status"]=="VALID_128"


def test_multi_token_first_event():
    m=StreamMeasure(4,1.0)
    m.feed({"content":"ab","tokens":[5,6]},1.4)
    m.feed({"content":"cd","tokens":[7,8]},1.6)
    m.feed({"stop":True,"stop_type":"limit"},1.7)
    r=m.finalize()
    assert r["first_event_multi_token"] is True
    assert r["first_event_token_count"]==2
    assert r["status"]=="VALID_128"


def test_short_output():
    m=StreamMeasure(4,1.0)
    m.feed({"content":"x","tokens":[9]},1.2)
    m.feed({"stop":True,"stop_type":"eos"},1.3)
    r=m.finalize()
    assert r["status"]=="SHORT_OUTPUT"
    assert r["finish_reason"]=="eos"


def test_timeout():
    m=StreamMeasure(4,1.0)
    m.feed({"content":"x","tokens":[9]},1.2)
    m.timeout(2.0)
    r=m.finalize()
    assert r["status"]=="INCOMPLETE"
    assert r["finish_reason"]=="timeout"


def test_incomplete_eof():
    m=StreamMeasure(4,1.0)
    m.feed({"content":"x","tokens":[9]},1.2)
    m.t_done=1.5
    r=m.finalize()
    assert r["status"]=="INCOMPLETE"


def test_classifier():
    assert classify_output(128,128,"length")=="VALID_128"
    assert classify_output(57,128,"stop")=="SHORT_OUTPUT"
    assert classify_output(17,128,None,False)=="INCOMPLETE"


for fn in [
    test_empty_then_tokens,
    test_multi_token_first_event,
    test_short_output,
    test_timeout,
    test_incomplete_eof,
    test_classifier,
]:
    fn()
    print("PASS",fn.__name__)
print("PERF_ADAPTER_SELFTEST_PASS")
