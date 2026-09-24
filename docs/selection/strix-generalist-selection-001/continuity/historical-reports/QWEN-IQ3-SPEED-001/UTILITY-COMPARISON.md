# IQ3 utility versus recorded GLM checks

2026-09-06. Final offline utility audit of **A target-only and B MTP+ngram N4/p-min0.75**, after both completed12 requests. No model requests, code re-execution, service operations or frozen-runner edits by this audit.

**Both arms pass4/4 fixed reasoning answers and8/8 recorded sandboxed code checks, with natural EOS throughout. B is faster than A on each of these12 individual observations. But B is not target-exact:** seven utility outputs differ in token IDs from A, in addition to the public performance fidelity/repeat failures. The functional checks show useful answers on this small set; they do not qualify the speculative implementation or establish equal intelligence.

## Protocol differences that remain explicit

A/B are Qwen3.8-Flash-Next UD-IQ3_XXS on **one** Strix Halo, HIP, ctx8192, F16 K/V, recipe SSD/mmap/lazy placement; B adds MTP+ngram N4/p-min0.75. Both have identical runtime/model maps, target parameters and utility requests. GLM is the preserved CIRU-IU4 target TP2/DFlash2 k5 on **two** Strix Halo. Models, quantization formats, templates and hardware allocation differ; this IQ3 local stage is preparatory, not a two-node result.

The four user prompts and answer validators are identical. Both use temperature0/seed1, but Qwen uses explicit **xhigh/enable_thinking=true, cap4096**; GLM uses **reasoning_effort=max, cap1536**. These named reasoning settings are not assumed equivalent. Prompt/output tokenization and answer lengths differ. No matching prose, reasoning text, token IDs or logits is required between models. Every answer below ended naturally before its cap; none was forced to reach512 generated tokens.

## Four shared reasoning problems

All table cells are **single observations**, except the separately labeled GLM confirmation below. HTTP includes the whole request through final response; decode is the runtime's after-first-token rate, not time to obtain the answer. No pooled TPS median across unrelated prompts.

| Task | Correct answer checks A /GLM | A input/output | GLM input/output | A HTTP s /decode tok/s | Historical GLM HTTP s /decode tok/s |
|---|---|---:|---:|---:|---:|
| money_arithmetic | PASS /PASS | 164/486 | 119/339 | 22.073123 /23.324673 | 11.581516 /30.923658 |
| shortest_path | PASS /PASS | 162/306 | 127/207 | 13.998752 /23.440624 | 9.726838 /22.639522 |
| lru_trace | PASS /PASS | 168/587 | 128/314 | 26.095990 /23.413997 | 14.638628 /22.357660 |
| code_output_reasoning | PASS /PASS | 202/360 | 160/332 | 16.386671 /23.390988 | 12.116494 /29.043887 |

The historical GLM outputs report297/188/279/307 reasoning tokens respectively. No separately measured reasoning-token count is inferred for Qwen from text length or by re-tokenizing it. Neither Qwen arm reached4096; A completions were306–587 tokens. Higher token throughput on an individual problem would not automatically mean a quicker answer because the number of generated tokens differs.

### B on the same four requests

| Task | Correct answer check | B input/output | B HTTP seconds | B HTTP tok/s | B decode tok/s | Accepted/drafted |
|---|---|---:|---:|---:|---:|---:|
| money_arithmetic | PASS | 164/375 | 11.904604 | 31.500418 | 35.384700 | 258/275 |
| shortest_path | PASS | 162/306 | 9.932563 | 30.807760 | 34.083711 | 220/284 |
| lru_trace | PASS | 168/418 | 14.419490 | 28.988542 | 31.310646 | 273/318 |
| code_output_reasoning | PASS | 202/368 | 13.026430 | 28.250257 | 30.644694 | 256/418 |

These are four different **single** xhigh observations, not a pooled reasoning median. B reduces all four observed completion times relative to A, partly with different output lengths. Against the historical GLM singles, B is slightly quicker on LRU and slower on the other three; those near differences are not a repeated head-to-head speed gate. No utility xhigh observation is93 tok/s.

**Stronger repeated GLM reference, same code problem:** the later OPT004 confirmation has one excluded warmup plus **three** measured natural332-token answers with identical messages,307 reported reasoning tokens. Recomputed medians: **11.906347 HTTP seconds,27.884288 HTTP tok/s,29.696141 decode tok/s**, server TTFT743.602535ms. Compare with A's **single**16.386671-second/360-token observation and B's **single**13.026430-second/368-token observation; neither singleton is a median. Do not mix the older GLM singleton into the three-run median. This reference is a different prompt from G0's109/256 benchmark, not a new GLM speed optimization.

Client TTFT is unavailable for these nonstreaming runs. GLM's server TTFT is a different measurement; Qwen `prompt_ms` must not be relabeled TTFT.

## Eight published executable-code tasks: both IQ3 arms

These use the published thinkingOFF/cap1200 request policy, **not xhigh reasoning**. Each arm has one generation and one saved sandbox execution per task; all ended with natural stop. The pinned prompts/assertions are the existing public code-qual corpus, not newly designed favorable questions.

| Task | Saved sandbox A /B | Output tokens A /B | HTTP seconds A /B | Decode tok/s A /B |
|---|---|---:|---:|---:|
| balanced | PASS /PASS | 98 /98 | 4.665108 /3.270728 | 23.347412 /35.625471 |
| rle | PASS /PASS | 106 /106 | 4.945218 /2.821613 | 23.386952 /44.710493 |
| merge_intervals | PASS /PASS | 142 /142 | 6.450616 /4.673704 | 23.498535 /33.487518 |
| lru | PASS /PASS | 223 /223 | 10.028434 /6.918850 | 23.429429 /34.991974 |
| csv_sum | PASS /PASS | 84 /93 | 4.025906 /3.105321 | 23.319467 /35.079665 |
| regex_ip | PASS /PASS | 125 /146 | 5.743537 /4.673455 | 23.487171 /34.675706 |
| fib_arith | PASS /PASS | 94 /94 | 4.538106 /2.630758 | 23.368120 /45.421578 |
| topo | PASS /PASS | 200 /211 | 9.058785 /6.134984 | 23.370715 /37.735198 |

There is **no corresponding GLM eight-code baseline** in the comparison evidence, and none was run for this audit. No eight-code improvement/regression against GLM can be claimed. Passing these few assertions is not proof that each function handles all unspecified edge cases or is production-ready.

## Functional success is not target fidelity

Additional **offline-only** comparisons of the already saved A/B utility outputs used their identical build/quant/request contract. Five tasks have exact full native token IDs/text: shortest_path, balanced, rle, merge_intervals, fib_arith. Seven differ despite passing their functional validator:

| Task | First differing generated-token index, zero-based |
|---|---:|
| money_arithmetic | 179 |
| lru_trace | 12 |
| code_output_reasoning | 72 |
| lru | 182 |
| csv_sum | 52 |
| regex_ip | 23 |
| topo | 178 |

This is a comparison of one existing response per arm/task, **not a repeated utility-fidelity benchmark**, and makes no cross-model token comparison with GLM. It reinforces the separate public result: B code5 observed median93.156025 tok/s, range32.318668–96.678573, with a strong sequence trend, **repeat FAIL921 /target FAIL26**; prose median23.086579, repeat FAIL160 /target FAIL13. These performance numbers are thinkingOFF and **not qualified**. No functional PASS removes those failures; no cause or kernel correction is inferred here, and no additional model requests are authorized by them.

## Independent raw audit and limits

All24 A/B intents match the pinned task requests. Saved response-body base64, byte lengths and parsed JSON agree; native counts/stop/timings were independently revalidated and matched the saved derived metrics. Every A draft counter is zero as required by target-only mode; B reports nonzero draft counters in all12 cases. The four expected JSON answers were rejudged for each arm from raw responses with the existing validator, without trusting summary PASS flags.

For all16 programs across A/B, each saved extracted source and held test exactly matches the raw final content and pinned test corpus. All saved sandbox receipts show exit0, no timeout, empty stderr and the expected completion-marker format. Generated code was also inspected read-only. **Execution results are verified retained receipts, not newly re-executed tests**; the original isolated execution and its limits are documented in `HARNESS-REUSE.md`. The utility evidence does not override any separate repeat/target-fidelity result from public performance runs.

## Raw paths and provenance

Campaign root: `/home/funboy/ai-exp/reports/moe-cluster/QWEN-IQ3-SPEED-001/`.

- `a-utility/protocol.json`, `summary.json`, `sandbox-preflight.json`.
- For each task ID in the tables: `a-utility/<id>-intent.json`, `<id>-raw.json`, `<id>-result.json`; executable cases also have `<id>-code.json` with the exact tested source/assertions.
- Protocol SHA256`b4b758f7bdcf547c0e9e3f092860e7bb754e1a5cb3847260b71fe5284b90bcc7`; summary SHA256`c10b22a29a88887808418d18c8a139efbde0f90c4d29a96293f1686673afdb4b`.
- `b-utility/` has the identical file pattern for all12 tasks; protocol SHA256`d247e9c41237b9a1c953c512854a74189f79426a5c2564a8aba10d927e1cc48c`, summary SHA256`afa86d4d551998dd606b92c32336d5d403e6a11de892e5e43b98b66cad74a6fa`.
- Separate public performance summaries: `b-public/summary.json`, `b-code5/summary.json`, their protocols/raw and referenced original A samples; not part of the utility score.
- `public-source/harness/code-qual.py`, source pin/hashes and adapter details in `HARNESS-REUSE.md`; no remote source is executed.

Historical GLM four-task root: `/home/funboy/ai-exp/reports/moe-cluster/CIRU-TP2-001/dflash5-f1-wmma-003/quality/`, `protocol.json`, `task-01.json` through`task-04.json`, and their request files. Protocol SHA256`8b2d65019ef581c5c4df16127d0e33b4b97e4e6536e8c7f45fe85ec11646c532`.

| GLM raw | SHA256 |
|---|---|
| `task-01.json` | `b97ce5528e017fa4b36607c16aadcb0a31eaa554395a9e5f1a56095e2ec548bb` |
| `task-02.json` | `b6c718f6a82473a89646ce973a7195fe45c8704a170006d50f596d94d0619c94` |
| `task-03.json` | `083cc7164b066b5be1e976a835c0a3cf2b5802f481737c47762005c784debccf` |
| `task-04.json` | `1c22bef720797a26482aebc6cb1b3cb25edd0cd6d099825ec7dab26e6cae3be8` |

Repeated GLM code reference: `/home/funboy/ai-exp/reports/moe-cluster/CIRU-TP2-001/opt004-restore-k5-001/quality-confirmation/`, `00-raw.json` excluded warmup, `01-raw.json`–`03-raw.json` measurements, protocol/summary. Its full hashes and audit are in `/home/funboy/ai-exp/reports/moe-cluster/GLM-CIRU-OPT-004/CONFIRMATION-RESULT.md`; all three measurement bodies and metrics were rechecked for this comparison.
