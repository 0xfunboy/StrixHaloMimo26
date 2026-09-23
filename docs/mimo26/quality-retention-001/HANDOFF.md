# QUALITY-RETENTION-001 — consegna terminale

PHASE: TERMINAL_COMPLETE
LAST_DELIVERY_HEALTH_AT: 2026-09-23T14:10:45+0200
REPO: /home/funboy/StrixHaloMimo26
BRANCH: perf/mimo26-strix
ENTRY_COMMIT: fb432c37f96c4514e763bb49f57614d9696efe79
PREPARATION_COMMIT: 6c32e7509db1920c2e78c985ff913c8c8d83af18
SOURCE_INDEX_SHA256: 9f60624b3a68269cae973efc239426a285b13e3c7de982dcb3f662c7b0ebf337
DELIVERY_COMMIT: the local commit containing this handoff; read git log for its exact ID. No circular self-reference.

## Risultati verificati

A mixed21/24 PASS (2 FAIL_SEMANTIC,1 FAIL_FORMAT). B originale21/24 PASS (3 FAIL_SEMANTIC).
20 BOTH_PASS;2 BOTH_FAIL;1 A_FAIL_B_PASS (REASON-03);1 A_PASS_B_FAIL (DOC-03).
Tutte le24 coppie valutabili. Zero cap/incompleti, errori tecnici, validator bloccati o violazioni critiche preregistrate osservate.
SOURCE_FREEZE=PASS; INPUT_COMPARABILITY=PASS; SANITY_PREFLIGHT/POSTFLIGHT=PASS_BOTH; EXPERIMENT_COMPLETION=COMPLETE.
GENERAL_QUALITY_EQUIVALENCE=NOT_ESTABLISHED; QUANTIZATION_ONLY_EFFECT=NOT_ISOLATED.
LONG_CONTEXT/CONCURRENCY/MTP_DFLASH=NOT_EVALUATED; PRODUCTION_PROMOTION=NOT_PERFORMED.

REASON-03: A calcola correttamente ma usa total_censes invece di total_cents; schema non riparato.
DOC-03: B classifica correttamente NOT_RUN ma omette la citazione E3 richiesta.
REASON-02: A scelta ammissibile subottimale; B supera il budget.
REASON-04: entrambi perdono il tie-break sul rischio e dichiarano il costo del percorso errato.
Dettagli in FINDINGS.md e nelle coppie canoniche, senza adattamento dei validator dopo i risultati.

## Run e restore

A: /home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-A-mixed-001
B: /home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-B-original-001
Entrambi: un solo caricamento,24 casi+6 sanity pre+6 post,36 record primari, worker exit0, NORMAL_COMPLETION.
A restore PASS2026-09-23T13:33:46+02:00. B restore PASS2026-09-23T13:55:22+02:00.
K2 dspark-k2-gfx1151 release5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513, DS41/RUNNING epoch1790164228979629195, rank0/rank1/paired HTTP200.
I processi vLLM EngineCore superstiti appartengono ai cgroup DS41 residenti, non a residui MiMo. Own worker/supervisor inattivi e PID modelli precedenti assenti; lock liberi nel controllo registrato. Non fermare K2.
Timestamp e perimetri distinti in final-live.json; ultima health read-only in delivery-live.json.

## Artefatti / verifica

ROOT: /home/funboy/StrixHaloMimo26/docs/mimo26/quality-retention-001/
PROTOCOL.md,cases.jsonl,expected.jsonl,sanity.jsonl,source-manifest.json,sources/,source-SHA256SUMS: preregistrati e invariati.
REPORT.md,summary.json,paired-results.jsonl,raw-results.jsonl: generati dal valutatore congelato; raw-results è indice derivato dichiarato.
FINDINGS.md: interpretazione degli errori, non nuovo validator.
evidence/:276 copie byte-identiche di artefatti originali, manifest/hash, raw rank1 peer verificato.
verification.json e verification/evaluation-check.stdout: ricalcolo CPU PASS, originali e release sources invariati.
cluster-docs-update.json: checkpoint globale finale aggiornato; vecchio CURRENT preservato in archivio.
I due script di packaging posthoc non cambiano preregistrazione, risposte o scoring.

Comando effettivamente verificato:

```bash
cd /home/funboy/StrixHaloMimo26
PYTHONDONTWRITEBYTECODE=1 python3 docs/mimo26/quality-retention-001/sources/evaluate.py --root docs/mimo26/quality-retention-001 --check
```

Il comando non genera token: ricalcola i verdict sui raw esistenti e usa il sandbox Podman isolato già verificato per il codice. Richiede i percorsi originali presenti su NODE01 e l'immagine locale pinned. Nessuna pretesa di portabilità su una macchina priva di tali evidenze.

## NEXT EXACT ACTION

Consegnare questi risultati, preservare raw, sorgenti e K2. Nessun nuovo run, replay, tuning, deployment o push è autorizzato. Un nuovo holdout realistico è soltanto proposto in FINDINGS.md e richiede mandato separato. PERF-BASELINE-001 resta terminale PARTIAL_ENGINE_DECODE_ONLY; non riaprire le sue lacune storiche.
