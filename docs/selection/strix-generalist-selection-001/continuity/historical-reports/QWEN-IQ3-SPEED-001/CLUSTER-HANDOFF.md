# QWEN-IQ3-SPEED-001: bounded two-EVO handoff assessment

2026-09-06. **NO EXISTING QUALIFIED TWO-EVO PATH IN THE AUTHORIZED SCOPE.**
This is not a claim that the hardware or model makes distributed inference
impossible. It is the result of a bounded read-only inspection of the already
local EngramHalo source, controller and pinned audits. No network fetch,
download, build, service action, GPU/model request or runtime change was made.

## What the local IQ3 campaign establishes

- A, target-only EngramHalo/IQ3/F16: code23.486569 and prose23.487348 decode
  TPS medians; three1000-token measurements per category repeat exactly.
  The separate utility screen passed4/4 reasoning tasks and8/8 sandboxed code
  tasks with natural completion. This is a **limited local correctness/utility
  screen**, not general intelligence equivalence, long-context qualification,
  a promoted default, or a two-node result.
- B, the same target with EasiiX MTP Q8 plus `ngram-mod`: all-five code median
  **93.156025 TPS observed**, but repeat fails at zero-based token921 and all
  five diverge from A at token26. Prose median23.086579 TPS also fails repeat
  and target reference. Therefore there is **no qualified exact accelerated
  local candidate** to distribute. Functional utility, whatever its outcome,
  cannot cancel these failures.
- Code samples rise32.318668→81.002445→94.379426→96.678573→93.156025 TPS.
  The retained ngram history matters: this is neither an isolated MTP speed
  nor a demonstrated fresh-code speed. No speculative distributed extrapolation
  or expected two-EVO TPS is justified.

Raw evidence, relative to this report's directory:
`a-public/summary.json`, `a-utility/summary.json`, `b-public/summary.json`,
`b-code5/summary.json`; requests/results and provenance are retained alongside
each summary. Source/weight-format identity is in `SOURCE-RECIPE-AUDIT.md` and
`artifact-verification.json`. The master PLAN section16.14 records the chronology.

## Existing code paths: actual prerequisites and limits

Source root below is `/home/funboy/ai-exp/src/EngramHalo.cpp`, HEAD
`930918c59767aafcedb11149f5f855f1367afcdd`, with the already documented local
HIP host-buffer workaround. The recipe engine pin differs only in documentation.

| Path | Concrete local source evidence | Handoff and qualitative cost |
| --- | --- | --- |
| Generic layer split through RPC | `common/arg.cpp:2671` registers RPC; `:2821` offers layer splitting. The existing cluster controller `scripts/cluster.py:404` selects local ROCm plus RPC and layer placement. | This is the explicitly excluded old Qwen layer-RPC path, not a new overlap engine. Configuration/worker deployment would be relatively small work, but its unresolved qualification and the user's exclusion are decisive. Do not relaunch or reuse the22:78 split. |
| `--split-mode row` over local HIP + remote RPC | `src/llama-model.cpp:1092` requires the device backend's `ggml_backend_split_buffer_type`, and `:1112` throws if unavailable. `ggml/src/ggml-rpc/ggml-rpc.cpp:2259` exports only RPC add/start-server hooks, not split-buffer support. | It is **not an existing cross-host row-parallel shortcut**. Providing split-buffer/compute/communication support would require backend development and fresh correctness qualification, not an extra launcher flag; outside scope. |
| Experimental tensor/Meta split over RPC | `src/llama-arch.cpp:1095` nominally allows qwen4exp through its default branch; that is only an architecture allow-list, not a successful graph or state test. `common/arg.cpp:2826` labels tensor mode experimental. PLAN16.1 records the prior Qwen Meta/RPC worker buffer-bounds initialization failure; current controller `scripts/cluster.py:378` blocks it. | Existing generic entry points are real, but no qualified IQ3/EngramHalo inter-host implementation was demonstrated. The prior failure was another recorded Qwen configuration, not proof that every future build fails. Fixing/porting this path is a research/backend integration effort with unknown qualification cost and is explicitly excluded now. |
| Enable RCCL and treat the two EVOs as two local GPUs | Actual `build-hip/CMakeCache.txt:510` has HIP_RCCL OFF. Even the source's enabled branch uses `ncclCommInitAll` with local device IDs (`ggml/src/ggml-cuda/ggml-cuda.cu:1189`); device enumeration is the local HIP backend. | A rebuild flag does not supply cross-host rank orchestration or make a remote EVO a local HIP device. This is not an existing turnkey network TP path; a new distributed integration would be required. No driver/build change is proposed. |
| Put MTP/draft on the second EVO | `common/arg.cpp:4205` has independent draft device placement and `common/speculative.cpp:2431` copies the draft devices into its context. RPC could expose another device, but the presence of a placement option proves neither target/draft overlap nor equivalence. | Explicitly excluded remote-drafter direction. B already fails local repeat/reference; moving it does not repair that. Existing synchronous placement could be cheap to configure, but a correct useful overlapping implementation and its evidence are absent, with substantial unbounded qualification work. |
| Put only the PLE table on remote RAM | The actual recipe is local mmap/lazy read. `src/models/qwen4exp.cpp:1359` queues local mapped-row prefetch; `src/llama-model.cpp:1816` tracks tensors still in that mapping and `:1835` calls `llama_mmap::prefetch_rows`. Offloaded nonmapped tensors do not retain this lazy mapped-row path. | No dedicated remote PLE row service/transport is provided by this path. A generic remote weight override is not the same SSD/lazy recipe, nor evidence of speed acceleration. A dedicated implementation would be new memory/transport work with separate correctness, failure and capacity qualification; outside scope. |

The controller paths above are relative to
`/home/funboy/ai-exp/strix-moe-cluster/`. Its IQ3 profile intentionally selects
only `ROCm0`, launches no RPC worker, owns only the local unit, and rejects
distributed/trace/Q5 variants (`scripts/cluster.py:264,368`). Thus there is no
hidden existing IQ3 two-node preset to promote.

Two independent target-only replicas would be ordinary request-level capacity,
not one shared model using both GPUs for the same stream. Replication would
require explicit service/ownership planning, a checked local model copy and
screening on node02; that replica was not inspected or launched here. Its
deployment cost is qualitatively smaller than a new inference backend, but it
does not meet the requested single-stream distributed objective and cannot
replace the retained GLM pair by implication.

The pinned alternatives audit
`../QWEN-QUAL-001/ALTERNATIVE-SOURCE-AUDIT.md` already found no demonstrated
Qwen TP2 implementation in the inspected Halogen repository. CIRU's retained
GLM TP2 runtime uses another model implementation/weight format; its existence
does not establish Qwen IQ3 support. No alternate runtime was re-researched or
ported for this handoff.

## Precise next prerequisite; no new experiment authorized

There is **no next distributed launch command within this campaign**. Retain
A's local screen as evidence and label B's high code TPS as nonexact. Complete
the already authorized campaign handoff and restore the exact retained GLM
pair; do not reopen Q5, layer-RPC, Meta/RPC, remote draft or a new pipeline.

A future single-stream Qwen cluster step first needs an identifiable existing
implementation, at a pinned source revision, explicitly covering this
qwen4exp architecture and its PLE/recurrent state on **two separate gfx1151
hosts**. It must preserve or explicitly reconcile the original IQ3 format and
template, document the actual network/backend path, and have evidence of
correctness beyond a launch flag. Parent/user authorization must then name the
newly allowed path and its bounded same-target local/distributed verification.
For a speculative path, repeat and target-reference failures must be resolved
under that authorization before any exact speed claim. No numeric speed or
elapsed engineering-time estimate is available from the present evidence.
