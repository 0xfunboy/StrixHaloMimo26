# StrixHaloMimo26 — QUALITY-RETENTION-001

**Stato esperimento:** `COMPLETE`. Valutazione indipendente appaiata sul pannello sintetico preregistrato.

A = mixed Baekpica, singolo Strix, llama.cpp HIP pinned. B = originale Xiaomi FP8/MXFP4, due Strix, vLLM TP2 pinned; non un oracolo infallibile.

## Esiti sul pannello

| Voce | Risultato |
|---|---|
| Casi pianificati per braccio | 24 |
| A | PASS: 21, FAIL_SEMANTIC: 2, FAIL_FORMAT: 1 |
| B | PASS: 21, FAIL_SEMANTIC: 3 |
| Coppie effettivamente valutabili | 24/24 |
| A FAIL / B PASS | 1 |
| Regressioni critiche | 0 |
| Incompleti al cap | 0 |
| Errori tecnici / casi non eseguiti | 0 |
| Validator bloccati / revisione / casi invalidi | 0 |

## Tutte le coppie

| ID | Famiglia | A | B | Esito appaiato | Critico A / B |
|---|---|---|---|---|---|
| CODE-01 | Codice | PASS | PASS | BOTH_PASS | 0 / 0 |
| CODE-02 | Codice | PASS | PASS | BOTH_PASS | 0 / 0 |
| CODE-03 | Codice | PASS | PASS | BOTH_PASS | 0 / 0 |
| CODE-04 | Codice | PASS | PASS | BOTH_PASS | 0 / 0 |
| DEBUG-01 | Debugging | PASS | PASS | BOTH_PASS | 0 / 0 |
| DEBUG-02 | Debugging | PASS | PASS | BOTH_PASS | 0 / 0 |
| DEBUG-03 | Debugging | PASS | PASS | BOTH_PASS | 0 / 0 |
| DEBUG-04 | Debugging | PASS | PASS | BOTH_PASS | 0 / 0 |
| STRUCT-01 | Dati strutturati | PASS | PASS | BOTH_PASS | 0 / 0 |
| STRUCT-02 | Dati strutturati | PASS | PASS | BOTH_PASS | 0 / 0 |
| STRUCT-03 | Dati strutturati | PASS | PASS | BOTH_PASS | 0 / 0 |
| STRUCT-04 | Dati strutturati | PASS | PASS | BOTH_PASS | 0 / 0 |
| DOC-01 | Documenti | PASS | PASS | BOTH_PASS | 0 / 0 |
| DOC-02 | Documenti | PASS | PASS | BOTH_PASS | 0 / 0 |
| DOC-03 | Documenti | PASS | FAIL_SEMANTIC | A_PASS_B_FAIL | 0 / 0 |
| DOC-04 | Documenti | PASS | PASS | BOTH_PASS | 0 / 0 |
| OPS-01 | Diagnosi e pianificazione | PASS | PASS | BOTH_PASS | 0 / 0 |
| OPS-02 | Diagnosi e pianificazione | PASS | PASS | BOTH_PASS | 0 / 0 |
| OPS-03 | Diagnosi e pianificazione | PASS | PASS | BOTH_PASS | 0 / 0 |
| OPS-04 | Diagnosi e pianificazione | PASS | PASS | BOTH_PASS | 0 / 0 |
| REASON-01 | Ragionamento vincolato | PASS | PASS | BOTH_PASS | 0 / 0 |
| REASON-02 | Ragionamento vincolato | FAIL_SEMANTIC | FAIL_SEMANTIC | BOTH_FAIL | 0 / 0 |
| REASON-03 | Ragionamento vincolato | FAIL_FORMAT | PASS | A_FAIL_B_PASS | 0 / 0 |
| REASON-04 | Ragionamento vincolato | FAIL_SEMANTIC | FAIL_SEMANTIC | BOTH_FAIL | 0 / 0 |

## Risultati per famiglia

| Famiglia | A | B | Coppie |
|---|---|---|---|
| Codice | {"PASS": 4} | {"PASS": 4} | {"BOTH_PASS": 4} |
| Debugging | {"PASS": 4} | {"PASS": 4} | {"BOTH_PASS": 4} |
| Dati strutturati | {"PASS": 4} | {"PASS": 4} | {"BOTH_PASS": 4} |
| Documenti | {"PASS": 4} | {"PASS": 3, "FAIL_SEMANTIC": 1} | {"BOTH_PASS": 3, "A_PASS_B_FAIL": 1} |
| Diagnosi e pianificazione | {"PASS": 4} | {"PASS": 4} | {"BOTH_PASS": 4} |
| Ragionamento vincolato | {"PASS": 1, "FAIL_SEMANTIC": 2, "FAIL_FORMAT": 1} | {"PASS": 2, "FAIL_SEMANTIC": 2} | {"BOTH_PASS": 1, "BOTH_FAIL": 2, "A_FAIL_B_PASS": 1} |

## Errori, regressioni e violazioni critiche

### DOC-03 — A_PASS_B_FAIL

**A: PASS.** 
Risposta originale: `/home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-A-mixed-001/requests/panel__DOC-03/result.json`.

**B: FAIL_SEMANTIC.** independent expected structure/value mismatch
Risposta originale: `/home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-B-original-001/requests/panel__DOC-03/result.json`.

### REASON-02 — BOTH_FAIL

**A: FAIL_SEMANTIC.** independent expected structure/value mismatch
Risposta originale: `/home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-A-mixed-001/requests/panel__REASON-02/result.json`.

**B: FAIL_SEMANTIC.** independent expected structure/value mismatch
Risposta originale: `/home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-B-original-001/requests/panel__REASON-02/result.json`.

### REASON-03 — A_FAIL_B_PASS

**A: FAIL_FORMAT.** independent expected structure/value mismatch
Risposta originale: `/home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-A-mixed-001/requests/panel__REASON-03/result.json`.

**B: PASS.** 
Risposta originale: `/home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-B-original-001/requests/panel__REASON-03/result.json`.

### REASON-04 — BOTH_FAIL

**A: FAIL_SEMANTIC.** independent expected structure/value mismatch
Risposta originale: `/home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-A-mixed-001/requests/panel__REASON-04/result.json`.

**B: FAIL_SEMANTIC.** independent expected structure/value mismatch
Risposta originale: `/home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-B-original-001/requests/panel__REASON-04/result.json`.


## Provenienza, sanity e restore

- A: `quality-retention-001-A-mixed-001`, 36 record richieste incluse sanity, caricamenti 1; worker `PASS`; sanity pre `PASS`, post `PASS`; restore `True`.
  Raw SHA256: `9021b395ab8e3f398921fddfdc3c9e92700cff2922687b271677b3a605762575`. Cleanup: `{"at": "2026-09-23T13:33:46+0200", "k2_state": "READY", "status": "PASS"}`.
- B: `quality-retention-001-B-original-001`, 36 record richieste incluse sanity, caricamenti 1; worker `PASS`; sanity pre `PASS`, post `PASS`; restore `True`.
  Raw SHA256: `bc5deeab16979d3dd473b8cb98a56760663ae83156c46fc33cbdbe8232015351`. Cleanup: `{"at": "2026-09-23T13:55:22+0200", "k2_state": "READY", "status": "PASS"}`.

Source index SHA256: `9f60624b3a68269cae973efc239426a285b13e3c7de982dcb3f662c7b0ebf337`.
Preregistrazione: `2026-09-23T13:23:07+0200`. Una generazione per caso, EOS naturale, nessun best-of, correzione con feedback o replay.

Ultima verifica live: `{"schema": "mimo26-quality-final-live-v1", "status": "PASS", "observation_completed_at": "2026-09-23T14:03:35+02:00", "health_and_unit_checks_at": "2026-09-23T13:58:06+02:00", "original_pid_absence_and_release_path_checks_at": "2026-09-23T14:00:30+02:00", "resident_engine_cgroup_checks_at": "2026-09-23T14:03:35+02:00", "nodes": {"NODE01": {"hostname": "01-EVO-X3", "user": "funboy", "boot_id": "43c6daec-31c3-4ebe-a599-54b69cfa92b6"}, "NODE02": {"hostname": "02-EVO-X3", "user": "funboy", "boot_id": "3fd0da44-da79-4480-ac6f-9a73ee121f17", "access": "SSH from NODE01 using 02-evo-x3-tb"}}, "controller": {"path": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6/runtime/ds41/serve-controller.sh", "state": "READY", "preset": "dspark-k2-gfx1151", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513", "owner": "DS41", "owner_state": "RUNNING", "epoch": "1790164228979629195", "rank0_health_http": 200, "rank1_health_http": 200, "paired_backend_http": 200}, "resident_units": {"NODE01_rank0": {"unit": "ds41-rank0.service", "active": true, "pid": 642280, "invocation_id": "9be4424aeadb4a679bc18a18447a71ba"}, "NODE02_rank1": {"unit": "ds41-rank1.service", "active": true, "pid": 653577, "invocation_id": "285e8d925fe34124baf38c736bab063a"}, "NODE01_paired": {"unit": "ds41-haloclu-pair.service", "active": true, "pid": 257070, "invocation_id": "4facab11bc2242c6b42117c9865c79b0"}}, "owner_receipt_invocations_match_units": true, "resident_launch_path_both_nodes": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6/runtime/ds41/launch-node.sh", "own_campaign_units": {"mimo26-qr001-supervisor-a-001.service": "not-found/inactive/MainPID0", "mimo26-qr001-supervisor-b-001.service": "not-found/inactive/MainPID0", "mimo26-qr001-a-r0-001.service": "not-found/inactive/MainPID0", "mimo26-qr001-b-r0-001.service": "not-found/inactive/MainPID0", "NODE02:mimo26-qr001-b-r1-001.service": "not-found/inactive/MainPID0"}, "original_model_pids_confirmed_absent": {"NODE01": [631703, 637819], "NODE02": [636285]}, "remaining_engine_processes_are_resident_not_mimo_residues": {"NODE01": {"pid": 642546, "name": "VLLM::EngineCor", "cgroup": "/user.slice/user-1000.slice/user@1000.service/app.slice/ds41-rank0.service"}, "NODE02": {"pid": 653760, "name": "VLLM::EngineCor", "cgroup": "/user.slice/user-1000.slice/user@1000.service/app.slice/ds41-rank1.service"}}, "matching_compute_or_cleanup_lock_holders": [], "native_cleanup_receipts": {"A": "2026-09-23T13:33:46+02:00", "B": "2026-09-23T13:55:22+02:00"}, "scope": "Read-only verification after both authorized windows. Separate timestamps are retained for each observation. No additional model generation or lifecycle transition performed for this verification."}`.

## Gate terminali

```json
{
  "EXPERIMENT_COMPLETION": "COMPLETE",
  "SOURCE_FREEZE": "PASS",
  "INPUT_COMPARABILITY": "PASS",
  "SANITY_PREFLIGHT": {
    "A": "PASS",
    "B": "PASS"
  },
  "SANITY_POSTFLIGHT": {
    "A": "PASS",
    "B": "PASS"
  },
  "QUALITY_PANEL_A": {
    "PASS": 21,
    "FAIL_SEMANTIC": 2,
    "FAIL_FORMAT": 1
  },
  "QUALITY_PANEL_B": {
    "PASS": 21,
    "FAIL_SEMANTIC": 3
  },
  "PAIRED_REGRESSIONS": 1,
  "CRITICAL_REGRESSIONS": 0,
  "INCOMPLETE_CASES": 0,
  "TECHNICAL_ERRORS": 0,
  "REVIEW_REQUIRED": 0,
  "GENERAL_QUALITY_EQUIVALENCE": "NOT_ESTABLISHED",
  "QUANTIZATION_ONLY_EFFECT": "NOT_ISOLATED",
  "LONG_CONTEXT": "NOT_EVALUATED",
  "CONCURRENCY": "NOT_EVALUATED",
  "MTP_DFLASH": "NOT_EVALUATED",
  "PRODUCTION_PROMOTION": "NOT_PERFORMED",
  "RESTORE_STATUS": {
    "A": "PASS",
    "B": "PASS",
    "final_live": "PASS"
  }
}
```

## Limiti e utilizzo

Le risposte sono giudicate rispetto a specifiche, calcoli e unit test indipendenti, non rispetto al testo del riferimento B. Gli unit test di codice girano solo nel sandbox rootless Podman preregistrato, senza rete, mount host o GPU.
Il pannello usa input brevi ed espliciti, per metà italiani e per metà inglesi. Non misura capacità su compiti aperti, contesti lunghi, concorrenza, tool reali o produzione. Le tool call dei casi diagnostici sono soltanto dati simulati.
Un errore critico osservato esclude l’uso autonomo per quel tipo di compito. Anche tutti i casi PASS giustificherebbero soltanto una proposta di pilot circoscritto e supervisionato, mai una promozione automatica.

## Riproduzione CPU-only

```bash
cd /home/funboy/StrixHaloMimo26
PYTHONDONTWRITEBYTECODE=1 python3 docs/mimo26/quality-retention-001/sources/evaluate.py --root docs/mimo26/quality-retention-001 --check
```

Il comando verifica gli hash e ricalcola i verdict senza inferenza, usando il medesimo sandbox disponibile e gli stessi validator congelati. `raw-results.jsonl` della consegna è un indice derivato delle risposte originali, non un log retrodatato.

## Passo successivo proposto, non eseguito

Una campagna separata con casi holdout più realistici e preregistrati, concentrata sulle famiglie fallite o sui limiti non coperti; nessuna modifica di questo lotto dopo gli output.

PERF-BASELINE-001 resta terminale PARTIAL_ENGINE_DECODE_ONLY e non viene modificata da questi tempi diagnostici.
