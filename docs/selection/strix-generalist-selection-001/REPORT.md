# STRIX-GENERALIST-SELECTION-001

**Collection:** PARTIAL_OR_BLOCKED. Scores are separate from execution and restore.

## Quality and operating cost

| Profile | Runtime qualification | Nodes | PASS / 12 | Other states | All task seconds | Successful task seconds | Native output tokens |
|---|---|---:|---:|---|---:|---:|---:|
| Q — Qwen3.8-Flash-Next AgenticRequant Q5K | PASS | 1 | 3 | {"INCOMPLETE_OUTPUT_CAP": 8, "FAIL_FORMAT": 1} | 1883.1639338210225 | 305.54599652902107 | 56841 |
| M — MiMo-V2.6 Flash RL mixed IQ2/Q8 | NOT_QUALIFIED_OR_INCOMPLETE | 1 | 0 | {"NOT_RUN": 12} | None | None | 0 |
| D — DeepSeek-V4.1-Flash Q2 E1 Engram concurrent | PASS | 2 | 3 | {"INCOMPLETE_OUTPUT_CAP": 9} | 4054.679925022996 | 780.820531386009 | 60783 |
| O — MiMo-V2.6 Flash RL original FP8/MXFP4 | NOT_QUALIFIED_OR_INCOMPLETE | 2 | 0 | {"NOT_RUN": 12} | None | None | 0 |

Times include failed and incomplete requests. O is an offline-generate observer; Q/M/D are local HTTP observers. No cross-observer normalized ratio is reported.

## All twelve matched tasks

| Case | Family | Q | M | D | O |
|---|---|---|---|---|---|
| CODE-IT | CODE | INCOMPLETE_OUTPUT_CAP | NOT_RUN | INCOMPLETE_OUTPUT_CAP | NOT_RUN |
| CODE-EN | CODE | INCOMPLETE_OUTPUT_CAP | NOT_RUN | INCOMPLETE_OUTPUT_CAP | NOT_RUN |
| DATA-IT | DATA | PASS | NOT_RUN | PASS | NOT_RUN |
| DATA-EN | DATA | INCOMPLETE_OUTPUT_CAP | NOT_RUN | INCOMPLETE_OUTPUT_CAP | NOT_RUN |
| MATH-IT | MATH | INCOMPLETE_OUTPUT_CAP | NOT_RUN | INCOMPLETE_OUTPUT_CAP | NOT_RUN |
| MATH-EN | MATH | INCOMPLETE_OUTPUT_CAP | NOT_RUN | INCOMPLETE_OUTPUT_CAP | NOT_RUN |
| DOCS-IT | DOCS | INCOMPLETE_OUTPUT_CAP | NOT_RUN | INCOMPLETE_OUTPUT_CAP | NOT_RUN |
| DOCS-EN | DOCS | INCOMPLETE_OUTPUT_CAP | NOT_RUN | INCOMPLETE_OUTPUT_CAP | NOT_RUN |
| SCI-IT | SCIENCE | PASS | NOT_RUN | PASS | NOT_RUN |
| SCI-EN | SCIENCE | INCOMPLETE_OUTPUT_CAP | NOT_RUN | INCOMPLETE_OUTPUT_CAP | NOT_RUN |
| OPS-IT | OPS | FAIL_FORMAT | NOT_RUN | PASS | NOT_RUN |
| OPS-EN | OPS | PASS | NOT_RUN | INCOMPLETE_OUTPUT_CAP | NOT_RUN |

## Per-family results

### Q

```json
{
  "CODE": {
    "INCOMPLETE_OUTPUT_CAP": 2
  },
  "DATA": {
    "PASS": 1,
    "INCOMPLETE_OUTPUT_CAP": 1
  },
  "DOCS": {
    "INCOMPLETE_OUTPUT_CAP": 2
  },
  "MATH": {
    "INCOMPLETE_OUTPUT_CAP": 2
  },
  "OPS": {
    "FAIL_FORMAT": 1,
    "PASS": 1
  },
  "SCIENCE": {
    "PASS": 1,
    "INCOMPLETE_OUTPUT_CAP": 1
  }
}
```

### M

```json
{
  "CODE": {
    "NOT_RUN": 2
  },
  "DATA": {
    "NOT_RUN": 2
  },
  "DOCS": {
    "NOT_RUN": 2
  },
  "MATH": {
    "NOT_RUN": 2
  },
  "OPS": {
    "NOT_RUN": 2
  },
  "SCIENCE": {
    "NOT_RUN": 2
  }
}
```

### D

```json
{
  "CODE": {
    "INCOMPLETE_OUTPUT_CAP": 2
  },
  "DATA": {
    "PASS": 1,
    "INCOMPLETE_OUTPUT_CAP": 1
  },
  "DOCS": {
    "INCOMPLETE_OUTPUT_CAP": 2
  },
  "MATH": {
    "INCOMPLETE_OUTPUT_CAP": 2
  },
  "OPS": {
    "PASS": 1,
    "INCOMPLETE_OUTPUT_CAP": 1
  },
  "SCIENCE": {
    "PASS": 1,
    "INCOMPLETE_OUTPUT_CAP": 1
  }
}
```

### O

```json
{
  "CODE": {
    "NOT_RUN": 2
  },
  "DATA": {
    "NOT_RUN": 2
  },
  "DOCS": {
    "NOT_RUN": 2
  },
  "MATH": {
    "NOT_RUN": 2
  },
  "OPS": {
    "NOT_RUN": 2
  },
  "SCIENCE": {
    "NOT_RUN": 2
  }
}
```

## Failures and incomplete responses

### CODE-IT / Q — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001/requests/panel__CODE-IT/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### CODE-IT / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### CODE-IT / D — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-002/requests/panel__CODE-IT/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### CODE-IT / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### CODE-EN / Q — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001/requests/panel__CODE-EN/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### CODE-EN / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### CODE-EN / D — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-002/requests/panel__CODE-EN/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### CODE-EN / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### DATA-IT / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### DATA-IT / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### DATA-EN / Q — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001/requests/panel__DATA-EN/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### DATA-EN / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### DATA-EN / D — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-002/requests/panel__DATA-EN/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### DATA-EN / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### MATH-IT / Q — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001/requests/panel__MATH-IT/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### MATH-IT / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### MATH-IT / D — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-002/requests/panel__MATH-IT/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### MATH-IT / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### MATH-EN / Q — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001/requests/panel__MATH-EN/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### MATH-EN / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### MATH-EN / D — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-002/requests/panel__MATH-EN/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### MATH-EN / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### DOCS-IT / Q — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001/requests/panel__DOCS-IT/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### DOCS-IT / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### DOCS-IT / D — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-002/requests/panel__DOCS-IT/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### DOCS-IT / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### DOCS-EN / Q — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001/requests/panel__DOCS-EN/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### DOCS-EN / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### DOCS-EN / D — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-002/requests/panel__DOCS-EN/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### DOCS-EN / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### SCI-IT / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### SCI-IT / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### SCI-EN / Q — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001/requests/panel__SCI-EN/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### SCI-EN / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### SCI-EN / D — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-002/requests/panel__SCI-EN/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### SCI-EN / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### OPS-IT / Q — FAIL_FORMAT

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001/requests/panel__OPS-IT/result.json`.
```json
{
  "reason": "Expecting value: line 1 column 1 (char 0)",
  "critical_violations": [],
  "diagnostics": {
    "parsing": false,
    "schema": false
  }
}
```

### OPS-IT / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### OPS-IT / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### OPS-EN / M — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

### OPS-EN / D — INCOMPLETE_OUTPUT_CAP

Original: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-002/requests/panel__OPS-EN/result.json`.
```json
{
  "reason": null,
  "critical_violations": []
}
```

### OPS-EN / O — NOT_RUN

Original: `NOT_RUN`.
```json
{
  "reason": "No completed atomic request exists",
  "critical_violations": []
}
```

## Engine tasks, separate from reasoning quality

| Profile / input | n valid / 3 | Prompt engine tok/s median | Decode post-first engine tok/s median | D total decode rate (rounded native log) | Local request seconds median |
|---|---:|---:|---:|---:|---:|
| Q / ENGINE-2K | 3 | 478.29696373190353 | 29.009508037575305 | None | 8.904408925009193 |
| Q / ENGINE-8K | 3 | 485.7515125277992 | 27.859846108352425 | None | 21.71949519898044 |
| M / ENGINE-2K | 0 | None | None | None | None |
| M / ENGINE-8K | 0 | None | None | None | None |
| D / ENGINE-2K | 3 | 93.44 | None | 16.85 | 29.54757173699909 |
| D / ENGINE-8K | 3 | 147.14 | None | 16.67 | 63.14549605399952 |
| O / ENGINE-2K | 0 | None | None | None | None |
| O / ENGINE-8K | 0 | None | None | None | None |

All replicas, ranges, native timing contracts, actual input token/byte counts and resource snapshots are retained in summary.json. SHORT_OUTPUT is not padded. No client TTFT is invented. D rounded log totals are not the post-first-token metric.

## Collection, sanity and restore

Q: {"run": "/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001", "collection": "PASS", "records": 32, "launches": 1, "sanity": {"preflight": "PASS", "postflight": "PASS"}, "restore": true, "cleanup": {"status": "PASS", "k2_state": "READY", "at": "2026-09-24T10:53:53+0200", "epoch": "1790239745036780819", "target": {"controller": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6/runtime/ds41/serve-controller.sh", "release": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6", "preset": "dspark-k2-gfx1151", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513"}}, "issues": []}
M: {"run": "/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-M-001", "collection": "FAILED", "records": 6, "launches": 1, "sanity": {"preflight": "FAIL_OR_MISSING", "postflight": "FAIL_OR_MISSING"}, "restore": true, "cleanup": {"status": "PASS", "k2_state": "READY", "at": "2026-09-24T11:01:01+0200", "epoch": "1790240178624599071", "target": {"controller": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6/runtime/ds41/serve-controller.sh", "release": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6", "preset": "dspark-k2-gfx1151", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513"}}, "issues": []}
D: {"run": "/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-002", "collection": "PASS", "records": 32, "launches": 1, "sanity": {"preflight": "PASS", "postflight": "PASS"}, "restore": true, "cleanup": {"status": "PASS", "k2_state": "READY", "at": "2026-09-24T12:43:29+0200", "epoch": "1790246320305924015", "target": {"controller": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6/runtime/ds41/serve-controller.sh", "release": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6", "preset": "dspark-k2-gfx1151", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513"}}, "issues": []}
O: {"run": "/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-O-001", "collection": "FAILED", "records": 6, "launches": 1, "sanity": {"preflight": "FAIL_OR_MISSING", "postflight": "FAIL_OR_MISSING"}, "restore": true, "cleanup": {"status": "PASS", "k2_state": "READY", "at": "2026-09-24T16:23:52+0200", "epoch": "1790259544584609152", "target": {"controller": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6/runtime/ds41/serve-controller.sh", "release": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6", "preset": "dspark-k2-gfx1151", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513"}}, "issues": []}

## Blockers and bounded MTP

```json
{
  "profiles": {
    "M": {
      "status": "BLOCKED",
      "scope": "ISOLATED_TO_PROFILE",
      "reason": "The sampled thinking-ON sanity code_clamp response defines a function with an assignment but no return statement. All four sandbox checks returned None. The other five sanity cases passed; zero panel requests were sent. The preregistered sanity admission gate failed; no semantic retry or source repair is permitted.",
      "evidence": "continuity/M_SANITY_BLOCKER.md",
      "native_receipts": [
        "/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-M-001/sanity-pre.json",
        "/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-M-001/requests/preflight__SANITY-code_clamp/result.json"
      ],
      "raw_fatal_label": "TECHNICAL_ERROR / SANITY_PREFLIGHT_FAIL",
      "interpreted_cause": "SEMANTIC_SANITY_ADMISSION_FAILURE_NOT_DEMONSTRATED_RUNTIME_CORRUPTION",
      "panel_requests_sent": 0,
      "repeat": "NOT_PERFORMED",
      "continue_other_profiles_only_after_restore": true
    },
    "MTP": {
      "status": "BLOCKED",
      "scope": "ISOLATED_TO_MTP",
      "reason": "Our OFF collector expected an absent /props field. The actual native mode is default_generation_settings.params['speculative.types']='none'. Zero OFF reference completions were dispatched before the collector stopped; the primary Q load has ended, so ON lacks required matched references within the remaining load budget.",
      "evidence": "continuity/MTP_COLLECTOR_BLOCKER.md",
      "native_receipt": "/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001/mtp-off-blocker.json",
      "quality_primary_unchanged": true,
      "does_not_block_profiles": [
        "M",
        "D",
        "O"
      ],
      "extra_inference_to_recover": "NOT_AUTHORIZED_AUTOMATICALLY"
    },
    "O": {
      "status": "BLOCKED",
      "scope": "ISOLATED_TO_PROFILE",
      "reason": "Five of six sanity controls passed. SANITY-json returned correct alpha/beta values inside a Markdown fence, violating the explicit only-valid-JSON contract. Frozen all-six admission failed before any panel request. No semantic retry or fence repair.",
      "evidence": "continuity/O_SANITY_BLOCKER.md",
      "native_receipt": "/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-O-001/requests/preflight__SANITY-json/result.json",
      "raw_fatal_label": "TECHNICAL_ERROR / SANITY_PREFLIGHT_FAIL",
      "interpreted_cause": "FORMAT_SANITY_ADMISSION_FAILURE_NOT_DEMONSTRATED_RUNTIME_CORRUPTION",
      "panel_requests_sent": 0,
      "engine_benchmark_requests_sent": 0,
      "at": "2026-09-24T16:23:37+0200"
    }
  },
  "mtp": {
    "status": "BLOCKED_OFF_REFERENCE_COLLECTOR",
    "supersedes": "Original manifest static HTTP-toggle blocker only; process-level addendum preregistered before Q.",
    "OFF_records": 0,
    "ON_records": 0,
    "OFF_errors": [],
    "ON_errors": [],
    "pairs": [],
    "partial_acceptance_observed": false,
    "drafting_observed": false,
    "sampled_distribution_equivalence": "NOT_ESTABLISHED",
    "run": "/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-QMTP-001",
    "run_completion": "NOT_STARTED",
    "restore": null,
    "benchmarks": {
      "MTP-PERF-PROSE": {
        "OFF": {
          "count": 0,
          "n_valid": 0,
          "decode_tps": {
            "n": 0,
            "median": null,
            "min": null,
            "max": null,
            "sum": null
          },
          "request_seconds": {
            "n": 0,
            "median": null,
            "min": null,
            "max": null,
            "sum": null
          },
          "samples": []
        },
        "ON": {
          "count": 0,
          "n_valid": 0,
          "decode_tps": {
            "n": 0,
            "median": null,
            "min": null,
            "max": null,
            "sum": null
          },
          "request_seconds": {
            "n": 0,
            "median": null,
            "min": null,
            "max": null,
            "sum": null
          },
          "samples": []
        },
        "qualified_ratio": null,
        "admitted": false
      },
      "MTP-PERF-CODE": {
        "OFF": {
          "count": 0,
          "n_valid": 0,
          "decode_tps": {
            "n": 0,
            "median": null,
            "min": null,
            "max": null,
            "sum": null
          },
          "request_seconds": {
            "n": 0,
            "median": null,
            "min": null,
            "max": null,
            "sum": null
          },
          "samples": []
        },
        "ON": {
          "count": 0,
          "n_valid": 0,
          "decode_tps": {
            "n": 0,
            "median": null,
            "min": null,
            "max": null,
            "sum": null
          },
          "request_seconds": {
            "n": 0,
            "median": null,
            "min": null,
            "max": null,
            "sum": null
          },
          "samples": []
        },
        "qualified_ratio": null,
        "admitted": false
      }
    },
    "blockers": {
      "OFF": {
        "status": "BLOCKED",
        "phase": "mtp_off_after_primary_complete",
        "error": "RuntimeError:MTP_PROCESS_MODE_UNPROVEN:None",
        "primary_records_preserved": 32,
        "at": "2026-09-24T10:49:02+0200"
      }
    },
    "additional_model_loads": 0
  }
}
```

## Interpretation limits

Twelve new synthetic tasks, one sampled generation per profile; no statistical superiority or variance estimate.
D exposes native total generation count but not native generated IDs or separate reasoning/final counts; unavailable fields remain null.
Engine tasks have thinking OFF and must not replace reasoning task elapsed times.
Source manifests, timing observers and runtime configurations differ by model; the original O is not an oracle.

Static same-request two-node feasibility and the single next action are in COOPERATION.md and NEXT_EXACT_ACTION.md. No HaloPipe port, additional distributed workload, deployment or push is performed.

## CPU-only reproducibility

```bash
cd /home/funboy/StrixHaloMimo26
PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 python3 docs/selection/strix-generalist-selection-001/continuity/evaluate_continuity.py --root docs/selection/strix-generalist-selection-001 --check
```
Requires original native run paths and the pinned existing Podman image for code tests. This command is claimed verified only when verification.json records its successful exit.

## Continuity attestation

The original 74-file freeze and the pre-output 15-file addendum are separate and preserved. The Q adapter and process configuration were authorized and frozen in the addendum, not a post-output scoring change. Historical Qwen reports were recovered without rerunning the old tests.
