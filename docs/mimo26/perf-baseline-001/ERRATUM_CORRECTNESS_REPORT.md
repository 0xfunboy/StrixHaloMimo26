# Erratum — MiMo correctness reporting, verified recovery 2026-09-23

This does not replace the original September 22 correctness report or its raw files. The earlier erratum is preserved under `recovery-audit/prior-reports/`.

## Principal mixed run: resolved

`mixed-single-correctness-002`, llama.cpp `58367713a6935c0810103378144008df32e3d5db`; source `load.json`, finished 2026-09-22T19:22:24+0200.

| Observation | Bytes | GiB, bytes / 2**30 |
|---|---:|---:|
| Before | 127883239424 | 119.10054779052734 |
| After | 39059042304 | 36.37656784057617 |
| Difference | 88824197120 | 82.72397994995117 |

These are system MemAvailable observations, not exact GPU allocation or additive with RSS/PSS/GTT on UMA.

## Alternative GiB values: only partially resolved

The after-load value 36.54961013793945 GiB is exactly 38325044 kB from `mixed-tp1-llama-sanity-001/load.json`, finished 2026-09-22T20:21:30+0200.

No supporting raw receipt was found for the older before value 119.33901977539062 GiB (128139296768 bytes) or delta 82.78940963745117 GiB (88894451712 bytes) in the inspected confirmation load/result/events/logs. Their provenance remains **UNRESOLVED**. Arithmetic consistency with the after-value is not evidence of the observation that produced them. The preceding erratum's definite attribution of all three values to the confirmation run is therefore withdrawn.

## Diagnostic timing attribution: resolved

Recomputing medians from the five `quality.json` native timing records of `mixed-tp1-llama-sanity-001` gives prompt 57.02004473880432 tok/s and decode 20.24988356316951 tok/s. Every response identifies the confirmation runtime fingerprint `b11098-97845c4f1`.

Those values do not belong to the principal mixed runtime and are not included in PERF-BASELINE-001. Principal pre-campaign performance remains NOT_MEASURED; its six correctness sanity passes are unchanged.

Structured counterpart: `correctness-erratum.json`. Current performance audit: `REPORT.md` / `summary.json`.
