# C2 residual diagnostic: complete local match, unresolved trajectory mismatch

2026-09-06. Offline audit only. **Qwen C2 remains NON_PROMOTED; no causal operator was identified by this residual probe. C3 remains unspent.** This document adds no experiment, implementation, service action or permission to extend tracing.

## Evidence actually established

The `c2-residual` driver made exactly two cold code requests: a 44-token prompt, 160 generated tokens, temperature 0, seed 42, `cache_prompt=false`. Both completed with valid native responses, exactly reproduced the historical C2 MTP 160-token prefix, and still diverged from the same-build C2 target reference at emitted token index 146 (zero-based). This is a repeatable qualification failure, not a transport or incomplete-output failure.

The original Q5 target, shared Q8 MTP sidecar, xhigh profile and C2 flag `GGML_CUDA_QWEN_Q8_KV_VEC4=1` were retained. The actual trace selected position 169 within the authorized 167..189 interval. Its first input ID 513 equals emitted token 125 of the historical shared prefix; the complete shared prefix contains 44 prompt plus 146 emitted tokens, 190 IDs total.

The native replay completed all four target decodes: disarmed M4, disarmed M1, traced M1, traced M4. The same 121,082,036-byte sequence snapshot was restored byte-exactly three times, with reported frontier min=max=168 and actual RS3. Both traced captures completed, followed by a successful `pair_end` and, on shutdown, `session_end`.

- **48/48 layer boundaries** were present: `l_last-0` through `l_last-46`, plus `h_nextn` for layer 47.
- **79/79 selected output boundaries** matched bit-for-bit on the first logical token, including all layer boundaries, the selected layer 3 internals, embedding/mixer/head outputs.
- **13/13 captured direct activation input pairs** matched; 66 input-exclusion records across the two arms remain exclusions, not proof about every operand.
- M1 versus M4 first-row logits matched across **all 248,320 values**: zero differing elements, maxabs 0, RMSE 0, cosine 1. Each arm's disarmed/traced observer control independently produced that same row.
- The common logits SHA256 is `7d902cc031e0b668f48f520b0ed03ab72dccef28020829d64840b8263b328c7b`. The comparator reports `COMPLETE_LAYER_MATCH` and `first_comparable_divergence=null`.

## What this does not establish

This is **one first-row comparison at input position 169**, not verification of M4 rows 170..172, later blocks, the full generated trajectory, or a standalone target reference's internal state. Both replay arms start from the same current MTP-context snapshot; matching them does not prove that snapshot equals the state reached by the independent target-only trajectory. Equal preceding emitted IDs likewise do not prove equal recurrent/KV state.

The serialized snapshot does not cover every historical RS row or graph/allocator detail. Disarmed callbacks are not absent callbacks; full-logit observer controls constrain the captured first output row, not every intermediate state. Native FA operands were saved, but full cache future rows can legitimately differ between M1/M4 and were not declared equivalent by this audit.

Consequently the residual data neither identifies a new failing operator nor justifies a speculative C3 kernel/state patch. It also cannot qualify frontend/API serving, 8K/32K context, quality, or TPS. The bounded residual probe is exhausted; the root's disposition is to stop this Qwen qualification attempt and restore the already qualified GLM configuration, without spending C3 on an unlocalized guess.

## Exact artifacts

All paths below are relative to `/home/funboy/ai-exp/reports/moe-cluster/QWEN-QUAL-001/`:

- `replay-residual-004/comparison.json`: complete offline comparison, boundaries, metrics, driver linkage and original binary receipts.
- `replay-residual-004/target.1437114.jsonl`, `.f32`, `.fa.bin`: native metadata, logical F32 values, native FA operands/output.
- `replay-residual-requests/{summary,prefix,reference,protocol,identity-before,identity-after}.json`: bounded protocol, case/prefix proof and runtime/model/candidate identity.
- `replay-residual-requests/code-{1,2}-{request,response,comparison,native-validation,http}.json` and corresponding response `.raw`: both complete failed-reference requests.
- `c2-target-measure/code-1-response.json` and `c2-mtp-measure/code-1-response.json`: historical 256-token references; exact source receipts are in the residual driver's `reference.json`.

After shutdown, final JSONL SHA256 is `02d68a68945540ba9ca334c479c048982a983f3277df37e0328004e9e833a511`. The comparator's earlier metadata SHA `d6929b427e1f9d7b93d1bb4d02685ce647f2c0854c992c83587773e5b88468c9` equals the final file with only its final successful `session_end` line removed; the payload was not rewritten. F32 SHA remains `d660fb1afbea6f69b0b4006c025bb7cd16f7d8e0a029bb16f21510ee30e3c768`; FA SHA remains `bb0b32d1581b2d6dccabb5b79ae67d034c31666be87345c275baf75dcbc69f47`.
