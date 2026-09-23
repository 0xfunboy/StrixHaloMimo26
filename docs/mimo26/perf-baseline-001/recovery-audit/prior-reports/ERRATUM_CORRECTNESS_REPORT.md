# Erratum — MIMO26 correctness report before PERF-BASELINE-001

Date: 2026-09-23

This file does not replace or delete the 2026-09-22 correctness report. It records two reporting corrections derived from the original raw artifacts before the performance campaign.

## 1. Mixed principal-run memory accounting

Authoritative principal run:

- run: mixed-single-correctness-002
- llama.cpp: 58367713a6935c0810103378144008df32e3d5db
- source: /home/funboy/.local/state/strixhalomimo26/windows/mixed-single-correctness-002/load.json

Raw counters from that run:

- MemAvailable before: 127883239424 bytes
- MemAvailable after load: 39059042304 bytes
- delta: 88824197120 bytes

Conversions generated directly from those byte counters with divisor 2**30:

- before: 119.10054779052734 GiB
- after: 36.37656784057617 GiB
- delta: 82.72397994995117 GiB

The older JSON fields 119.33901977539062 / 36.54961013793945 / 82.78940963745117 GiB do not belong to these principal-run byte counters. The after-load value 36.54961013793945 GiB maps to the confirmation run mixed-tp1-llama-sanity-001 raw value 38325044 kB. The corresponding older before/delta values came from that confirmation-run observation, not from the principal-run load.json.

For PERF-BASELINE-001, all GiB values are generated from byte counters from the same structured record and run.

## 2. Diagnostic timing attribution

The diagnostic medians:

- prompt throughput: 57.02004473880432 tok/s
- decode throughput: 20.24988356316951 tok/s

belong only to:

- run: mixed-tp1-llama-sanity-001
- runtime: 97845c4f1ffae096d22ad772df396550f9f78306

They are not measurements of the principal mixed run mixed-single-correctness-002 on runtime 58367713a6935c0810103378144008df32e3d5db.

The principal mixed run therefore has no qualified performance result before PERF-BASELINE-001.

## 3. Correctness status unchanged

These are reporting corrections only. They do not change:

- original TP2 correctness sanity: 6/6 PASS;
- mixed single-Strix correctness sanity: 6/6 PASS;
- quality retention vs original: NOT EVALUATED;
- long context: NOT EVALUATED;
- concurrency: NOT EVALUATED;
- MTP/DFlash: NOT EVALUATED.
