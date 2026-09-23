# QUALITY-HOLDOUT-002 — consegna locale terminale

PHASE: TERMINAL_COMPLETE
BASE_COMMIT: 0e2ae3708beaeec2adf5e993ce2091c2dba4220d
PREPARATION_COMMIT: 7be9a8ff066fa2b3ce442d5dd38de4e75147ea2b
SOURCE_INDEX_SHA256: 8487252d5d42b528dc1ff48ab1e640940bb994ae9c9d464654a527bccfbdd729
DELIVERY_COMMIT: resolve git log on this file after local delivery commit; no circular reference.

{
  "EXPERIMENT_COMPLETION": "COMPLETE",
  "PREREGISTRATION_AND_SOURCE_FREEZE": "PASS",
  "NATIVE_INPUT_COMPARABILITY": "PASS",
  "CACHE_REUSE_CHECK": "PASS_ZERO_REUSE",
  "SANITY_PRE": {
    "A": "PASS",
    "B": "PASS"
  },
  "SANITY_POST": {
    "A": "PASS",
    "B": "PASS"
  },
  "PANEL_A": {
    "FAIL_SEMANTIC": 9,
    "PASS": 9
  },
  "PANEL_B": {
    "PASS": 12,
    "FAIL_SEMANTIC": 6
  },
  "PAIRED_RESULTS": {
    "A_FAIL_B_PASS": 3,
    "BOTH_FAIL": 6,
    "BOTH_PASS": 9
  },
  "CRITICAL_VIOLATIONS": {
    "A": 0,
    "B": 0
  },
  "TECHNICAL_ERRORS": 0,
  "INCOMPLETE": 0,
  "CASE_INVALID": 0,
  "SERIAL_WINDOWS": "PASS",
  "RESTORE_STATUS": {
    "A": "PASS",
    "B": "PASS",
    "final_live": "PASS"
  },
  "GENERAL_EQUIVALENCE": "NOT_ESTABLISHED",
  "QUANTIZATION_ONLY_EFFECT": "NOT_ISOLATED",
  "PRODUCTION_PROMOTION": "NOT_PERFORMED",
  "THINKING_ON": "NOT_EVALUATED",
  "LONG_CONTEXT": "NOT_EVALUATED",
  "CONCURRENCY": "NOT_EVALUATED",
  "MTP_DFLASH": "NOT_EVALUATED"
}

RUN_A: /home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001
RUN_B: /home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001
ROOT: /home/funboy/StrixHaloMimo26/docs/mimo26/quality-holdout-002

SOURCE_FREEZE preserved, original evidence unchanged, closed001/PERF untouched, scratch preserved. Native nonstreaming collectors; no replay/repair/grammar. K2 restore and own PID/unit/lock checks in restore-A.json/final-live.json. Surviving DS41 EngineCore processes are legitimate residents.

CANONICAL: REPORT.md, summary.json, paired-results.jsonl, FINDINGS.md. Raw-results root is a derived index; evidence/ holds native copies and source hashes.
CPU_RECALCULATION_CHECK: PASS; command/dependencies in verification.json.

NEXT EXACT ACTION: deliver results and decision per family, then stop. No new inference, pilot, deployment, push or automatic experiment.
