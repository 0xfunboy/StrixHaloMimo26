# StrixHaloMimo26 - PERF-BASELINE-001

Date: 2026-09-23
Status: COMPLETE. Both arms terminal PASS, sanity before/after PASS, final K2 READY.

## Executive result

| Workload | A Mixed 1x Strix latency | B Original TP2 latency | A/B E2E rate | A native decode | B engine decode | A/B decode |
|---|---:|---:|---:|---:|---:|---:|
| 512->128 | 10.143 s | 39.244 s | 12.619 vs 3.262 tok/s (3.87x) | 19.070 tok/s | 3.417 tok/s | 5.58x |
| 2048->128 | 20.739 s | 45.547 s | 6.172 vs 2.810 tok/s (2.20x) | 18.990 tok/s | 3.417 tok/s | 5.56x |

For these frozen workloads the complete mixed single-Strix configuration has lower 128-token request latency and about 5.6x higher decode rate than the complete original TP2 configuration. This is a system-level comparison; it does not isolate quantization alone.

## Frozen workload

- Exact post-template input sizes: 512 and 2048 tokens.
- Tokenizer SHA256: ff15eb925890d6b71b5160de4b846fbd13178438ab463b38ecc953e8cd1dcb3e.
- Chat-template SHA256: 853650bee57bf95020373e4c928bd5a4b41b9915adf964a77711d2b49a291887.
- 512 token-ID SHA256: 493f138f2b4a01b1b265a43cfd0dd2e93019734628c42f971ddf5baca2c13468.
- 2048 token-ID SHA256: a231a3eac529907d19c316a7cae51de6deedcb0dbbc4eea260e9bdfbbfecaa02.
- Request order: 512, 2048, 2048, 512, 512, 2048.
- One 512 and one 2048 warmup per arm; warmups excluded.
- Actual sampling: temperature 0, seed 1, max output 128, ignore_eos false, thinking OFF.

## Arm A - Mixed IQ2/Q8, one Strix, llama.cpp

- Run: perf-baseline-001-A-mixed-001.
- Runtime commit: 58367713a6935c0810103378144008df32e3d5db.
- NODE01 only, HIP/gfx1151, Vulkan OFF, RPC OFF.
- Context 4096, batch 512, ubatch 128, one slot, no continuous batching, FA auto.
- cache_prompt false. Native cache_n=0 for all measured requests.
- Runtime tokenizer reproduced both frozen token sequences exactly.
- Cold load to health: 114.103 s.
- Sanity pre/post: PASS / PASS.

### A replicas

| Input | Rep | Latency s | Corrected E2E tok/s | Prompt ms | Prompt tok/s | Decode ms | Decode tok/s | cache_n | Output |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 512 | 1 | 10.167 | 12.590 | 3477.673 | 147.225 | 6661.791 | 19.064 | 0 | 128 |
| 2048 | 1 | 20.739 | 6.172 | 14050.349 | 145.762 | 6687.659 | 18.990 | 0 | 128 |
| 2048 | 2 | 20.760 | 6.166 | 14067.623 | 145.583 | 6691.081 | 18.980 | 0 | 128 |
| 512 | 2 | 10.138 | 12.625 | 3490.563 | 146.681 | 6646.618 | 19.107 | 0 | 128 |
| 512 | 3 | 10.143 | 12.619 | 3482.299 | 147.029 | 6659.646 | 19.070 | 0 | 128 |
| 2048 | 3 | 20.733 | 6.174 | 14090.582 | 145.345 | 6641.117 | 19.123 | 0 | 128 |

### A aggregate - median [min-max]

| Metric | 512->128 | 2048->128 |
|---|---:|---:|
| Request latency s | 10.143 [10.138-10.167] | 20.739 [20.733-20.760] |
| E2E output rate tok/s | 12.619 [12.590-12.625] | 6.172 [6.166-6.174] |
| Native prompt ms | 3482.299 [3477.673-3490.563] | 14067.623 [14050.349-14090.582] |
| Native prompt tok/s | 147.029 [146.681-147.225] | 145.583 [145.345-145.762] |
| Native decode ms | 6659.646 [6646.618-6661.791] | 6687.659 [6641.117-6691.081] |
| Native decode tok/s | 19.070 [19.064-19.107] | 18.990 [18.980-19.123] |

### A SSE adapter correction

The raw SSE collector initially classified the six samples as OVER_OUTPUT. The raw JSONL remains untouched. Inspection showed additional leading placeholder token-id 0 events. Independent native evidence is consistent for every request: predicted_n=128, prompt_n=512/2048, cache_n=0, and server print_timing reports exactly 128 generated tokens. All extra collected IDs were leading zeros. The derived A dataset therefore uses native predicted_n as the authoritative output count.

Client-side SSE TTFT is N/A for A. Placeholder events precede real generation and the persisted raw stream does not retain enough event typing to reconstruct a trustworthy first-real-token timestamp. No TTFT is fabricated.

## Arm B - Original FP8/MXFP4, two Strix, vLLM TP2

- Run: perf-baseline-001-B-original-001.
- vLLM 0.1.0rc2.dev9+g9255fd9fb9.rocm100, Torch 2.13.0+rocm10.0.0.
- QKV #57508 backport SHA256: eeb66fefbf1b63459e5712c031399f2d24d9ac05956c97b4e979ad03b901be72.
- TP2 / PP1, text-only, eager, prefix cache OFF, triton_unfused MXFP4 MoE, TRITON_ATTN_DIFFKV.
- 1 GiB KV per rank; exact frozen prompt IDs and zero cached prompt tokens on every measured request.
- NODE02 script, patch and workload hashes matched NODE01.
- Cold load: 279.734 s.
- Sanity pre/post: PASS / PASS.

### B replicas

| Input | Rep | Latency s | E2E tok/s | Engine TTFT s | Engine decode s | Engine decode tok/s | Cached | Output |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 512 | 1 | 39.194 | 3.266 | 2.082 | 37.111 | 3.422 | 0 | 128 |
| 2048 | 1 | 45.525 | 2.812 | 8.356 | 37.169 | 3.417 | 0 | 128 |
| 2048 | 2 | 45.547 | 2.810 | 8.379 | 37.168 | 3.417 | 0 | 128 |
| 512 | 2 | 39.335 | 3.254 | 2.092 | 37.242 | 3.410 | 0 | 128 |
| 512 | 3 | 39.244 | 3.262 | 2.073 | 37.170 | 3.417 | 0 | 128 |
| 2048 | 3 | 45.969 | 2.784 | 8.312 | 37.656 | 3.373 | 0 | 128 |

### B aggregate - median [min-max]

| Metric | 512->128 | 2048->128 |
|---|---:|---:|
| Request latency s | 39.244 [39.194-39.335] | 45.547 [45.525-45.969] |
| E2E output rate tok/s | 3.262 [3.254-3.266] | 2.810 [2.784-2.812] |
| Engine TTFT s | 2.082 [2.073-2.092] | 8.356 [8.312-8.379] |
| Engine decode s | 37.170 [37.111-37.242] | 37.169 [37.168-37.656] |
| Engine decode tok/s | 3.417 [3.410-3.422] | 3.417 [3.373-3.417] |

Client TTFT is N/A for B because this arm used offline LLM.generate. The engine scheduled-to-first-token interval is reported separately and is not relabeled as HTTP client TTFT.

## Cross-arm comparison

| Workload | A latency | B latency | B/A latency | A E2E | B E2E | A/B E2E | A decode | B decode | A/B decode |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 512->128 | 10.143 s | 39.244 s | 3.87x | 12.619 | 3.262 | 3.87x | 19.070 | 3.417 | 5.58x |
| 2048->128 | 20.739 s | 45.547 s | 2.20x | 6.172 | 2.810 | 2.20x | 18.990 | 3.417 | 5.56x |

### Prefill / TTFT semantics

A exposes native llama.cpp prompt-processing time. B exposes vLLM engine scheduled-to-first-token. These are not the same metric, so no ratio is computed and input_tokens/TTFT is not called pure prefill throughput.
- A 512 native prompt median: 3482.299 ms.
- A 2048 native prompt median: 14067.623 ms.
- B 512 engine TTFT median: 2.082 s.
- B 2048 engine TTFT median: 8.356 s.

## Resource / contamination checks

### A mixed
- Process read I/O during six measured requests: 0 bytes.
- Major faults during measured requests: 0.
- VmSwap was 0 before and after every request.
- Sampled gfx temperature range: 58.75-66.88 C.
- Sampled gfx clock range: 2197-2444 MHz.
- Sampled APU power range: 72.11-79.33 W.

### B original TP2
- Process read I/O during six measured requests: 81920 bytes total.
- Major faults during measured requests: 11 total.
- The rank0 process already had about 0.82 GiB VmSwap resident, but it was essentially stable during requests; only tiny read-I/O / fault deltas were observed.
- Sampled NODE01 gfx temperature range: 58.38-62.12 C.
- Sampled NODE01 gfx clock range: 2570-2763 MHz.
- Sampled NODE01 APU power range: 72.48-81.74 W.

No evidence of an active SSD/offload bottleneck appears in the request windows. TP2 communication cost is included in B end-to-end latency but was not isolated by this campaign. The earlier SCP link test is not used as a collective-latency measurement.

## Guards and final state

- A sanity pre/post: PASS / PASS.
- B sanity pre/post: PASS / PASS.
- All six A requests: native prompt_n exact, cache_n=0, native predicted_n=128.
- All six B requests: exact prompt IDs, num_cached_tokens=0, output=128.
- No measured request was excluded from the final aggregate.
- A cleanup PASS; B cleanup PASS.
- Final K2 READY; rank0/rank1 HTTP200; paired backend HTTP200.

## Reporting corrections carried forward

- Principal mixed correctness-run memory counters are 127883239424 -> 39059042304 bytes, i.e. 119.10055 -> 36.37657 GiB, delta 82.72398 GiB.
- The older 57.02 / 20.25 tok/s diagnostic medians belong only to confirmation run mixed-tp1-llama-sanity-001 on 97845c4f1 and are not used as the baseline here.

## Scope limits

This campaign establishes which complete configuration is faster on these two workloads. It does not establish IQ2 quality equivalence, long-context retention, concurrency behavior, MTP/DFlash performance, Vulkan performance, PP2 performance, or isolated Thunderbolt collective overhead.

## Artifacts

- execution-manifest.json: actual executed config/provenance.
- workloads.json: frozen text and token IDs.
- samples.csv: all 12 measured replicas.
- summary.json: aggregate statistics.
- arm-A-corrected.jsonl and arm-A-SSE-correction.json: derived A correction; raw evidence untouched.
- arm-B-normalized.jsonl: normalized B samples.
- evidence/A and evidence/B: copied terminal raw evidence.
- ERRATUM_CORRECTNESS_REPORT.md and correctness-erratum.json: pre-campaign reporting fixes.
