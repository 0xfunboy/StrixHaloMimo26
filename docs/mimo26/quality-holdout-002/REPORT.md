# StrixHaloMimo26 — QUALITY-HOLDOUT-002

**Esperimento: COMPLETE.** Score e completamento restano separati. Nessuna promozione o esperimento successivo.

18 nuove fixture sintetiche: sei JSON, sei EVIDENCE, sei CONSTRAINT; 9 IT e9 EN. Famiglie scelte alla luce dei fallimenti001, non campione cieco rappresentativo.
A: mixed Baekpica b3794b22, llama.cpp58367713 HIP, singolo Strix. B: Xiaomi5711b268 FP8/MXFP4, vLLM9255fd9 TP2, due Strix. Context4096, thinking OFF, nessuna grammar/repair/solver fornito al modello.

## Risultati per famiglia

| Famiglia | A | B | Coppie |
|---|---|---|---|
| JSON | {"FAIL_SEMANTIC": 5, "PASS": 1} | {"FAIL_SEMANTIC": 3, "PASS": 3} | {"A_FAIL_B_PASS": 2, "BOTH_FAIL": 3, "BOTH_PASS": 1} |
| EVIDENCE | {"PASS": 6} | {"PASS": 6} | {"BOTH_PASS": 6} |
| CONSTRAINT | {"FAIL_SEMANTIC": 4, "PASS": 2} | {"FAIL_SEMANTIC": 3, "PASS": 3} | {"A_FAIL_B_PASS": 1, "BOTH_FAIL": 3, "BOTH_PASS": 2} |

Coppie valutabili: 18/18. Nessun caso eliminato dal denominatore. Totali A: {"FAIL_SEMANTIC": 9, "PASS": 9}; B: {"FAIL_SEMANTIC": 6, "PASS": 12}.

## Tutte le18 coppie

| Caso | Input token | Cap | A | B | Coppia |
|---|---:|---:|---|---|---|
| JSON-01 | 1368 | 1024 | FAIL_SEMANTIC | PASS | A_FAIL_B_PASS |
| JSON-02 | 861 | 512 | FAIL_SEMANTIC | FAIL_SEMANTIC | BOTH_FAIL |
| JSON-03 | 1665 | 512 | FAIL_SEMANTIC | FAIL_SEMANTIC | BOTH_FAIL |
| JSON-04 | 1024 | 1024 | FAIL_SEMANTIC | PASS | A_FAIL_B_PASS |
| JSON-05 | 1104 | 512 | FAIL_SEMANTIC | FAIL_SEMANTIC | BOTH_FAIL |
| JSON-06 | 946 | 512 | PASS | PASS | BOTH_PASS |
| EVIDENCE-01 | 2507 | 1024 | PASS | PASS | BOTH_PASS |
| EVIDENCE-02 | 1985 | 512 | PASS | PASS | BOTH_PASS |
| EVIDENCE-03 | 2599 | 512 | PASS | PASS | BOTH_PASS |
| EVIDENCE-04 | 2100 | 1024 | PASS | PASS | BOTH_PASS |
| EVIDENCE-05 | 2479 | 512 | PASS | PASS | BOTH_PASS |
| EVIDENCE-06 | 2095 | 512 | PASS | PASS | BOTH_PASS |
| CONSTRAINT-01 | 1147 | 1024 | PASS | PASS | BOTH_PASS |
| CONSTRAINT-02 | 903 | 512 | FAIL_SEMANTIC | PASS | A_FAIL_B_PASS |
| CONSTRAINT-03 | 1009 | 512 | FAIL_SEMANTIC | FAIL_SEMANTIC | BOTH_FAIL |
| CONSTRAINT-04 | 812 | 512 | FAIL_SEMANTIC | FAIL_SEMANTIC | BOTH_FAIL |
| CONSTRAINT-05 | 942 | 1024 | FAIL_SEMANTIC | FAIL_SEMANTIC | BOTH_FAIL |
| CONSTRAINT-06 | 771 | 512 | PASS | PASS | BOTH_PASS |

## Errori e diagnostiche

### JSON-01 — Manifesto annidato di ordini consolidati

**A: FAIL_SEMANTIC**. $.shipments[0].contact: atteso "a@example.invalid", ricevuto null $.shipments[0].customer_id: atteso "C-01", ricevuto "C-09" $.shipments[0].items: atteso 2, ricevuto 1 $.shipments[0].items[0].qty: atteso 1, ricevuto 5 $.shipments[0].order_id: atteso "0003", ricevuto "0007" $.shipments[0].units: atteso 4, ricevuto 5 $.shipments[1].contact: atteso null, ricevuto "" $.shipments[1].customer_id: atteso "C-09", ricevuto "C-02" $.shipments[1].items[0].qty: atteso 5, ricevuto 7 $.shipments[1].items[0].sku: atteso "AA-01", ricevuto "DD-04" $.shipments[1].order_id: atteso "0007", ricevuto "0100" $.shipments[1].units: atteso 5, ricevuto 7 $.shipments[1].warehouse: atteso "W1", ricevuto "W2" $.shipments[3].contact: atteso "", ricevuto "a@example.invalid" $.shipments[3].customer_id: atteso "C-02", ricevuto "C-01" $.shipments[3].items: atteso 1, ricevuto 2 $.shipments[3].items[0].qty: atteso 7, ricevuto 1 $.shipments[3].items[0].sku: atteso "DD-04", ricevuto "AA-01" $.shipments[3].order_id: atteso "0100", ricevuto "0003" $.shipments[3].units: atteso 7, ricevuto 4 $.shipments[3].warehouse: atteso "W2", ricevuto "W1"
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__JSON-01/result.json`.
**B: PASS**. Nessun errore osservato nel caso.
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__JSON-01/result.json`.

### JSON-02 — Presence-aware device patch reconciliation

**A: FAIL_SEMANTIC**. $.devices[0].enabled: atteso false, ricevuto true $.devices[5].changed[0]: atteso "contact", ricevuto "enabled" $.devices[5].changed[1]: atteso "enabled", ricevuto "label" $.devices[5].changed[2]: atteso "label", ricevuto "contact"
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__JSON-02/result.json`.
**B: FAIL_SEMANTIC**. $.enabled_count: atteso 3, ricevuto 2
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__JSON-02/result.json`.

### JSON-03 — Registro versionato con tombstone e spareggi

**A: FAIL_SEMANTIC**. $.active[2].color: atteso "violet", ricevuto "black" $.active[2].event_id: atteso "e09", ricevuto "e06" $.active[2].quantity: atteso 7, ricevuto 0 $.active_quantity: atteso 23, ricevuto 16 $.discarded_event_ids[3]: atteso "e06", ricevuto "e08" $.discarded_event_ids[4]: atteso "e08", ricevuto "e09"
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__JSON-03/result.json`.
**B: FAIL_SEMANTIC**. $.active[2].color: atteso "violet", ricevuto "black" $.active[2].event_id: atteso "e09", ricevuto "e06" $.active[2].quantity: atteso 7, ricevuto 0 $.active[3].color: atteso "orange", ricevuto "amber" $.active[3].event_id: atteso "e10", ricevuto "e11" $.active[3].quantity: atteso 8, ricevuto 1 $.active_quantity: atteso 23, ricevuto 9 $.discarded_event_ids[3]: atteso "e06", ricevuto "e08" $.discarded_event_ids[4]: atteso "e08", ricevuto "e09" $.discarded_event_ids[5]: atteso "e11", ricevuto "e10"
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__JSON-03/result.json`.

### JSON-04 — Line-level discounts, proportional returns and independent tax rounding

**A: FAIL_SEMANTIC**. $.lines[4].refund_cents: atteso 66, ricevuto 198 $.lines[4].remaining_net_cents: atteso 198, ricevuto 166 $.totals.payable_cents: atteso 1899, ricevuto 1867 $.totals.remaining_net_cents: atteso 1642, ricevuto 1610
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__JSON-04/result.json`.
**B: PASS**. Nessun errore osservato nel caso.
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__JSON-04/result.json`.

### JSON-05 — Importazione con precedenza degli scarti e deduplica dei soli validi

**A: FAIL_SEMANTIC**. $.accepted: atteso 3, ricevuto 6 $.accepted[1].id: atteso "X-02", ricevuto "X-03" $.accepted[1].row: atteso 8, ricevuto 3 $.accepted[1].sku: atteso "BB", ricevuto "CC" $.accepted[2].id: atteso "X-08", ricevuto "X-01" $.accepted[2].qty: atteso 3, ricevuto 7 $.accepted[2].row: atteso 10, ricevuto 4 $.accepted[2].sku: atteso "HH", ricevuto "DD" $.accepted_qty: atteso 9, ricevuto 18 $.counts.accepted: atteso 3, ricevuto 6 $.counts.rejected: atteso 7, ricevuto 4 $.rejected: atteso 7, ricevuto 4 $.rejected[1].reason: atteso "DISABLED", ricevuto "BAD_VALUE" $.rejected[1].row: atteso 3, ricevuto 5 $.rejected[2].reason: atteso "DUPLICATE", ricevuto "BAD_TYPES" $.rejected[2].row: atteso 4, ricevuto 7 $.rejected[3].row: atteso 5, ricevuto 9
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__JSON-05/result.json`.
**B: FAIL_SEMANTIC**. $.accepted: atteso 3, ricevuto 4 $.accepted[1].id: atteso "X-02", ricevuto "X-03" $.accepted[1].row: atteso 8, ricevuto 3 $.accepted[1].sku: atteso "BB", ricevuto "CC" $.accepted[2].id: atteso "X-08", ricevuto "X-05" $.accepted[2].qty: atteso 3, ricevuto 0 $.accepted[2].row: atteso 10, ricevuto 6 $.accepted[2].sku: atteso "HH", ricevuto "EE" $.counts.accepted: atteso 3, ricevuto 4 $.counts.rejected: atteso 7, ricevuto 6 $.rejected: atteso 7, ricevuto 6 $.rejected[1].reason: atteso "DISABLED", ricevuto "DUPLICATE" $.rejected[1].row: atteso 3, ricevuto 4 $.rejected[2].reason: atteso "DUPLICATE", ricevuto "BAD_VALUE" $.rejected[2].row: atteso 4, ricevuto 5 $.rejected[3].reason: atteso "BAD_VALUE", ricevuto "BAD_TYPES" $.rejected[3].row: atteso 5, ricevuto 7 $.rejected[4].reason: atteso "BAD_VALUE", ricevuto "DUPLICATE" $.rejected[4].row: atteso 6, ricevuto 8 $.rejected[5].reason: atteso "BAD_TYPES", ricevuto "BAD_VALUE" $.rejected[5].row: atteso 7, ricevuto 9
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__JSON-05/result.json`.

### CONSTRAINT-02 — Coverage-constrained two-zone pipeline selection

**A: FAIL_SEMANTIC**. cost 13 > budget 12 missing coverage format-B cost: dichiarato 11, ricalcolato 13 ottimalità primaria non soddisfatta ricalcolo indipendente: {"cost": 13, "ids": ["N2", "O1", "P1", "S1"], "risk": 3, "status": "OPTIMAL", "value": 27}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__CONSTRAINT-02/result.json`.
**B: PASS**. Nessun errore osservato nel caso.
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__CONSTRAINT-02/result.json`.

### CONSTRAINT-03 — Percorso con checkpoint ordinati e priorità costo-rischio-tempo

**A: FAIL_SEMANTIC**. cost: dichiarato 7, ricalcolato 9 time: dichiarato 8, ricalcolato 11 tie-break non soddisfatto ricalcolo indipendente: {"cost": 9, "path": ["S", "B", "P", "D", "Q", "T"], "risk": 1, "status": "OPTIMAL", "time": 11}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__CONSTRAINT-03/result.json`.
**B: FAIL_SEMANTIC**. cost: dichiarato 8, ricalcolato 9 risk: dichiarato 1, ricalcolato 2 tie-break non soddisfatto ricalcolo indipendente: {"cost": 9, "path": ["S", "B", "P", "C", "Q", "T"], "risk": 2, "status": "OPTIMAL", "time": 9}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__CONSTRAINT-03/result.json`.

### CONSTRAINT-04 — Risk-first route with a forbidden vertex and ordered coverage

**A: FAIL_SEMANTIC**. cost: dichiarato 7, ricalcolato 9 time: dichiarato 8, ricalcolato 10 ottimalità primaria non soddisfatta ricalcolo indipendente: {"cost": 9, "path": ["U", "H", "K", "M", "Z"], "risk": 1, "status": "OPTIMAL", "time": 10}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__CONSTRAINT-04/result.json`.
**B: FAIL_SEMANTIC**. cost: dichiarato 11, ricalcolato 10 risk: dichiarato 1, ricalcolato 0 time: dichiarato 12, ricalcolato 11 ricalcolo indipendente: {"cost": 10, "path": ["U", "H", "K", "N", "M", "Z"], "risk": 0, "status": "OPTIMAL", "time": 11}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__CONSTRAINT-04/result.json`.

### CONSTRAINT-05 — Assegnazione con competenze, precedenze, risorsa esclusiva e tie-break

**A: FAIL_SEMANTIC**. double booking W-A slot 2 cost: dichiarato 10, ricalcolato 11 ottimalità primaria non soddisfatta ricalcolo indipendente: {"assignments": [{"job": "J1", "slot": 0, "worker": "W-A"}, {"job": "J2", "slot": 0, "worker": "W-B"}, {"job": "J3", "slot": 1, "worker": "W-B"}, {"job": "J4", "slot": 2, "worker": "W-A"}, {"job": "J5", "slot": 2, "worker": "W-A"}], "cost": 11, "makespan": 3, "status": "OPTIMAL"}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__CONSTRAINT-05/result.json`.
**B: FAIL_SEMANTIC**. J3/J4: same slot forbidden cost: dichiarato 10, ricalcolato 11 ottimalità primaria non soddisfatta ricalcolo indipendente: {"assignments": [{"job": "J1", "slot": 0, "worker": "W-A"}, {"job": "J2", "slot": 0, "worker": "W-B"}, {"job": "J3", "slot": 1, "worker": "W-B"}, {"job": "J4", "slot": 1, "worker": "W-A"}, {"job": "J5", "slot": 2, "worker": "W-A"}], "cost": 11, "makespan": 3, "status": "OPTIMAL"}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__CONSTRAINT-05/result.json`.

## Decisione per famiglia, senza esecuzione di pilot

### JSON

A: **CONTAIN_OBSERVED_ERRORS_BEFORE_FAMILY_PILOT**. Casi riusciti: ["JSON-06"]. Errori da contenere: ["JSON-01", "JSON-02", "JSON-03", "JSON-04", "JSON-05"]. Altri stati: [].
B: **CONTAIN_OBSERVED_ERRORS_BEFORE_FAMILY_PILOT**. Casi riusciti: ["JSON-01", "JSON-04", "JSON-06"]. Errori da contenere: ["JSON-02", "JSON-03", "JSON-05"]. Altri stati: [].
Controlli eseguibili sui dati reali: strict parsing, duplicate/nonfinite rejection, schema and exact types; field invariants and recomputation from available input data.
Componenti dedicati ancora necessari, non implementati in produzione: task-specific semantic transformation checks without benchmark expected answers.
A validator can reject malformed or inconsistent data; it does not create the correct missing answer.
Only six targeted synthetic cases in this family. No autonomous use, production deployment, model equivalence or automatic next experiment.

### EVIDENCE

A: **SCOPED_SUPERVISED_PILOT_PROPOSAL_ONLY**. Casi riusciti: ["EVIDENCE-01", "EVIDENCE-02", "EVIDENCE-03", "EVIDENCE-04", "EVIDENCE-05", "EVIDENCE-06"]. Errori da contenere: []. Altri stati: [].
B: **SCOPED_SUPERVISED_PILOT_PROPOSAL_ONLY**. Casi riusciti: ["EVIDENCE-01", "EVIDENCE-02", "EVIDENCE-03", "EVIDENCE-04", "EVIDENCE-05", "EVIDENCE-06"]. Errori da contenere: []. Altri stati: [].
Controlli eseguibili sui dati reali: citation-ID existence, per-claim citation presence, record-scope and cutoff metadata checks.
Componenti dedicati ancora necessari, non implementati in produzione: semantic relevance, sufficient evidence coverage and contradictory-source resolution on unseen documents.
Expected claim values and sufficient citation sets are benchmark oracles, not an existing production evidence judge.
Only six targeted synthetic cases in this family. No autonomous use, production deployment, model equivalence or automatic next experiment.

### CONSTRAINT

A: **CONTAIN_OBSERVED_ERRORS_BEFORE_FAMILY_PILOT**. Casi riusciti: ["CONSTRAINT-01", "CONSTRAINT-06"]. Errori da contenere: ["CONSTRAINT-02", "CONSTRAINT-03", "CONSTRAINT-04", "CONSTRAINT-05"]. Altri stati: [].
B: **CONTAIN_OBSERVED_ERRORS_BEFORE_FAMILY_PILOT**. Casi riusciti: ["CONSTRAINT-01", "CONSTRAINT-02", "CONSTRAINT-06"]. Errori da contenere: ["CONSTRAINT-03", "CONSTRAINT-04", "CONSTRAINT-05"]. Altri stati: [].
Controlli eseguibili sui dati reali: feasibility and declared totals recalculated from the proposed plan and input constraints.
Componenti dedicati ancora necessari, non implementati in produzione: separate exact optimizer or optimality certificate for real problem sizes and tie-break rules.
A feasibility checker rejects invalid choices; replacing a solution with a solver answer would be a different treatment.
Only six targeted synthetic cases in this family. No autonomous use, production deployment, model equivalence or automatic next experiment.

## Provenienza e budget

Commit preparazione: `7be9a8ff066fa2b3ce442d5dd38de4e75147ea2b`.
Indice frozen SHA256: `8487252d5d42b528dc1ff48ab1e640940bb994ae9c9d464654a527bccfbdd729`. Sorgenti/validator/oracoli/configurazioni congelati prima di entrambi i run.
Per ogni famiglia quattro cap512 e due cap1024; massimo12288 output token per braccio, esclusi sanity. Ogni input+cap+256 <=4096; nessun input troncato.
Input effettivi e scostamenti dai range indicativi sono in preflight/tokenization.json. Nessun padding aggiunto per raggiungere un numero.
Ogni risposta naturale è giudicata da specifiche indipendenti. L’originale non definisce expected o citazioni ammesse. I due algoritmi esatti CONSTRAINT concordano prima dei modelli; almeno un caso è INFEASIBLE.
Nessun codice generato sul nodo host: il solo codice sanity viene testato nel sandbox rootless Podman qualificato, senza rete/mount host/GPU. I piani sono dati, non azioni.

## Sanity e restore

A: `quality-holdout-002-A-mixed-001`, 30 record primari, caricamenti 1, sanity pre/post PASS/PASS, cleanup {"at": "2026-09-23T20:44:01+0200", "k2_state": "READY", "status": "PASS"}.
B: `quality-holdout-002-B-original-001`, 30 record primari, caricamenti 1, sanity pre/post PASS/PASS, cleanup {"at": "2026-09-23T21:07:16+0200", "k2_state": "READY", "status": "PASS"}.
Il peer B è confrontato con i30 record primari e non conta come replica. Dettagli NODE01/NODE02 e timestamp separati in final-live.json.
Stato finale: {"controller": {"epoch": "1790190148187249730", "owner": "DS41", "owner_state": "RUNNING", "paired_backend_http": "200", "preset": "dspark-k2-gfx1151", "ranks": [{"active": true, "health_http": "200", "rank": 0}, {"active": true, "health_http": "200", "rank": 1}], "reason": "", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513", "state": "READY"}, "historical_restores": {"A": {"cleanup": {"at": "2026-09-23T20:44:01+0200", "k2_state": "READY", "status": "PASS"}, "controller": {"epoch": "1790188753526304189", "owner": "DS41", "owner_state": "RUNNING", "paired_backend_http": "200", "preset": "dspark-k2-gfx1151", "ranks": [{"active": true, "health_http": "200", "rank": 0}, {"active": true, "health_http": "200", "rank": 1}], "reason": "", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513", "state": "READY"}}, "B": {"cleanup": {"at": "2026-09-23T21:07:16+0200", "k2_state": "READY", "status": "PASS"}, "controller": {"epoch": "1790190148187249730", "owner": "DS41", "owner_state": "RUNNING", "paired_backend_http": "200", "preset": "dspark-k2-gfx1151", "ranks": [{"active": true, "health_http": "200", "rank": 0}, {"active": true, "health_http": "200", "rank": 1}], "reason": "", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513", "state": "READY"}}}, "identities": {"NODE01": ["01-EVO-X3", "funboy", "43c6daec-31c3-4ebe-a599-54b69cfa92b6"], "NODE02": ["02-EVO-X3", "funboy", "3fd0da44-da79-4480-ac6f-9a73ee121f17"]}, "matching_lock_holders": [], "note": "EngineCore in DS41 cgroups are restored residents, not MiMo residue. Read-only checks, no new generations or lifecycle transitions.", "observation_completed_at": "2026-09-23T21:07:46+0200", "observation_started_at": "2026-09-23T21:07:45+0200", "original_model_pid_absence": {"A:NODE01:682309": "ABSENT", "B:NODE01:687294": "ABSENT", "B:NODE02:687654": "ABSENT"}, "own_units": {"NODE02:mimo26-qh002-b-r1-001": {"ActiveState": "inactive", "ExecMainStatus": "0", "InvocationID": "", "LoadState": "not-found", "MainPID": "0", "Result": "success", "SubState": "dead"}, "mimo26-qh002-a-r0-001": {"ActiveState": "inactive", "ExecMainStatus": "0", "InvocationID": "", "LoadState": "not-found", "MainPID": "0", "Result": "success", "SubState": "dead"}, "mimo26-qh002-b-r0-001": {"ActiveState": "inactive", "ExecMainStatus": "0", "InvocationID": "", "LoadState": "not-found", "MainPID": "0", "Result": "success", "SubState": "dead"}, "mimo26-qh002-supervisor-a-001.service": {"ActiveState": "inactive", "ExecMainStatus": "0", "InvocationID": "", "LoadState": "not-found", "MainPID": "0", "Result": "success", "SubState": "dead"}, "mimo26-qh002-supervisor-b-001.service": {"ActiveState": "inactive", "ExecMainStatus": "0", "InvocationID": "", "LoadState": "not-found", "MainPID": "0", "Result": "success", "SubState": "dead"}}, "owner": {"epoch": "1790190148187249730", "owner": "DS41", "rank_invocations": {"0": "76db7c3c87a94936baa4603589fe4c38", "1": "58fa87b0ab8b460281c25da71deb8d05"}, "state": "RUNNING"}, "remaining_engine_cgroups": {"NODE01": [{"cgroup": "0::/user.slice/user-1000.slice/user@1000.service/app.slice/ds41-rank0.service", "name": "VLLM::EngineCor", "pid": 690617}], "NODE02": [{"cgroup": "0::/user.slice/user-1000.slice/user@1000.service/app.slice/ds41-rank1.service", "name": "VLLM::EngineCor", "pid": 709069}]}, "resident_units": {"0": {"ActiveState": "active", "ExecMainStatus": "0", "InvocationID": "76db7c3c87a94936baa4603589fe4c38", "LoadState": "loaded", "MainPID": "690346", "Result": "success", "SubState": "running"}, "1": {"ActiveState": "active", "ExecMainStatus": "0", "InvocationID": "58fa87b0ab8b460281c25da71deb8d05", "LoadState": "loaded", "MainPID": "708886", "Result": "success", "SubState": "running"}}, "schema": "mimo26-holdout-live-v1", "status": "PASS"}.

## Gate terminali

```json
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
```

## Ricalcolo CPU-only effettivo

```bash
cd /home/funboy/StrixHaloMimo26
PYTHONDONTWRITEBYTECODE=1 python3 docs/mimo26/quality-holdout-002/sources/evaluate.py --root docs/mimo26/quality-holdout-002 --check
```
Richiede gli artefatti originali nei percorsi del manifest e l’immagine Podman pinned localmente disponibile per i sanity. Non è una promessa di portabilità. Il ricalcolo non invia richieste ai modelli.
REPORT.md, summary.json, paired-results.jsonl e FINDINGS.md sono generati dalla stessa base canonica. raw-results.jsonl è un indice derivato dichiarato; i raw originali sono preservati.
La ricevuta CPU_RECALCULATION_CHECK è in verification.json, prodotta dal comando --check senza modificarne i risultati.

PERF-BASELINE-001 resta terminale PARTIAL_ENGINE_DECODE_ONLY; QUALITY-RETENTION-001 resta completata e separata. I tempi incidentali non sono un nuovo benchmark.
**Fine mandato:** consegna locale e stop. Nessun pilot, deployment, push, tuning o ulteriore esperimento automatico.
