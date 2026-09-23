# StrixHaloMimo26 / PERF-BASELINE-001 — handoff finale di recupero

TASK: StrixHaloMimo26 / PERF-BASELINE-001
PHASE: RESULTS_RECOVERY_COMPLETE_WITH_DOCUMENTED_GAPS
LAST_OBSERVED_AT: 2026-09-23T11:25:02.902002+02:00
REPO: /home/funboy/StrixHaloMimo26
BRANCH: perf/mimo26-strix
ENTRY_HEAD: 5c7cba732d4745143c4f0593306b80552dd8832d
DELIVERY_COMMIT: risolvere con `git log -1 --format=%H -- docs/mimo26/perf-baseline-001/REPORT.md` dopo il commit di questa consegna; nessun reset/checkout necessario.
DIRTY_SCOPE_AT_ENTRY: tracked clean; scratch preesistente in benchmarks/mimo26, docs/mimo26/evidence, patches e scripts/mimo26 preservato e non incluso nel commit.

## Accesso e ownership realmente verificati

Connettore StrixMCP — EVO 01, CodeGPT instance 87c984c579 / connection 3d3ba5ce24. NODE01 01-EVO-X3, funboy, boot 43c6daec-31c3-4ebe-a599-54b69cfa92b6. NODE02 02-EVO-X3, funboy, boot 3fd0da44-da79-4480-ac6f-9a73ee121f17, raggiunto DA NODE01 con alias SSH 02-evo-x3-tb, IdentityAgent=none, BatchMode=yes.

OWNER: DS41 / RUNNING; epoch 1790127186526215806.
RESTORE_TARGET: K2 dspark-k2-gfx1151, release 5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513.
CONTROLLER: /home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6/runtime/ds41/serve-controller.sh (letto integralmente; invocato soltanto status).
LIVE: READY, rank0/rank1/paired HTTP 200. Rank0 InvocationID 33434044db6a425daf6ad59583f4c983 / PID 504815; rank1 InvocationID 3825ea5966684a5b86bd7307cb632878 / PID 591266, coerenti con owner. Nessun candidato processo MiMo e nessun holder pertinente di lock nella scansione in sola lettura. Nessun servizio o processo fermato/riavviato.

## Run originali, non da rilanciare

A_RUN: /home/funboy/.local/state/strixhalomimo26/windows/perf-baseline-001-A-mixed-001
B_RUN: /home/funboy/.local/state/strixhalomimo26/windows/perf-baseline-001-B-original-001
JOB: entrambi terminali NORMAL_COMPLETION / PASS, un solo caricamento per braccio, worker exit 0. Nessun finalizer in corso trovato.
A: start 03:10:59+0200, restore 03:20:12+0200; worker storico 525e06a28fbd4e7ebd1e9141b9ec0454.
B: start 03:21:32+0200, restore 03:37:54+0200; rank0 storico 125fd73ce72940caaa2e6e6e470421ee, rank1 storico 67314989a0164996b1fb4a285314bfc4.
Le due ricevute ripristinano K2, non E1; il restore B coincide con l’epoch live. File result/config/load/quality/arm-result/events/frozen/restore verificati. Il progress A è nelle liste prompt_progress dei raw, non in un progress.json inventato.

## Audit completato, senza GPU

12 misure (512/2048→128, tre repliche ciascuna per A/B), quattro warmup separati. Ordine congelato identico 512,2048,2048,512,512,2048. Raw e arm-result corrispondono; copie evidence corrispondono; sei risultati/output di rank1 corrispondono a rank0 B. Tutte le completion mantengono 128 token reali, stop al cap naturale: A limit, B length. Zero riuso prefill nei contatori pertinenti. Input ID congelati e controlli effettivi dei runtime verificati; niente retokenizzazione inventata.

Sanity pre/post 6/6 per ciascun braccio; rivalidazione CPU-only degli output salvati con validator invariato. Il sanity A usava chat nonstreaming, non l’adapter SSE; token ID del sanity performance non furono salvati.

A collector contava 4/7 zero-ID di progress: correzione derivata, senza alterare raw o sostituire repliche. tokens_cached finale è la lunghezza del contesto dello slot; cache_n/progress.cache sono zero. Native decode usa 127 passi dopo il primo token. A mediana 19.0701/18.9902 tok/s; B 3.41672/3.41682 tok/s; rapporto engine A/B 5.58139/5.55785, rispettivamente 512/2048 input. HTTP A e offline B restano osservatori distinti per la latenza; nessun rapporto client normalizzato.

53 file originali dei run invariati. Dieci test specifici del nuovo audit CPU PASS; aggregazione e Markdown/JSON riproducibili con --check. Nessun test QKV, fixture qualificata o benchmark preesistente ripetuto.

## Limiti terminali — non compensare con inferenza

1. TTFT client A non recuperabile: primo timestamp relativo al progress; manca il timestamp del primo vero token. B era offline, senza TTFT client. Prefill nativo A include primo sampling; scheduled→first B non è prefill puro. Nessuna ITL client o misura mancante ricostruita.
2. Originale perf_mixed_llama.py SHA 952c5583b5eda447862c9f803b2ecc14de6fc20a84e33bc16d03d6b2176a39c9 non trovato nelle copie locali/Git ispezionate. Lo script corrente modificato non viene usato come sorgente preregistrato. Il collector COMUNE originale è invece recuperato da NODE02, SHA a580585b901d15ecf70f65adb7c2510f0983a87be21ff81ea2e437ea8839d364.
3. Vecchi valori memoria 119.33901977539062GiB prima / 82.78940963745117GiB delta: nessuna ricevuta di origine trovata nel run di conferma. Soltanto il suo dopo 36.54961013793945GiB è attribuito dai raw. Il principale usa byte 127883239424→39059042304, delta 88824197120 e conversioni coerenti. Timing 57.02004473880432/ 20.24988356316951 soltanto nel run di conferma 97845c4f1, mai nella baseline attuale.
4. Snapshot risorse prima/dopo, non telemetria continua. VmSwap B non zero; rank0/rank1 misurano 11/7 major fault e 81920/73728 read byte; niente diagnosi automatica del collo di bottiglia.

GATES: CORRECTNESS_SANITY PASS; CACHE_VERIFIED PASS; K2_RESTORE PASS; PERFORMANCE_MEASUREMENT_COMPLETE PARZIALE (12/12 completion ma metriche client mancanti); METRICS_COMPARABLE PARTIAL_ENGINE_DECODE_ONLY; SOURCE_FREEZE PARZIALE. QUALITY_RETENTION_VS_ORIGINAL, LONG_CONTEXT, CONCURRENCY, MTP_DFLASH NOT_EVALUATED.

## Artefatti canonici e conservazione

CAMPAIGN_ROOT: /home/funboy/StrixHaloMimo26/docs/mimo26/perf-baseline-001
REPORTS: REPORT.md + summary.json, generati dallo stesso insieme; recovery-audit/audit.json identico allo structured summary.
DERIVED_SAMPLES: recovery-audit/normalized-results.jsonl; originale source_file/source_locator dichiarato per ogni record; include warmup distinti.
SOURCE_INDEX: recovery-audit/source-SHA256SUMS, tutte le 53 fonti originali; root SHA256SUMS per consegna.
RECOVERED_SOURCE: recovery-audit/perf_measure_common.frozen.py + source-recovery.json.
LIVE_RECEIPT: recovery-audit/live-reconciliation.json.
HISTORICAL_REPORTS: recovery-audit/prior-reports/. I vecchi raw/normalized JSONL rimangono intatti, non sono più i canonici. Vecchi PERF_BASELINE_001_REPORT.md/.json reindirizzano alla consegna verificata.
ERRATA: ERRATUM_CORRECTNESS_REPORT.md + correctness-erratum.json. Il report originale di correttezza è preservato.

WORKLOAD_SHA256: 905e3214673560903f60a396546e0e624f9851eccaea8c3cdd369924aecad5c6

Cluster docs aggiornati secondo AGENTS: CURRENT.md, projects/mimo26/PROJECT.md, singolo record evidence/results/MIMO26_PERF_BASELINE_001_RECOVERY_2026-09-23.md. Snapshot E1 precedente integralmente conservato in archive/CURRENT_PRE_MIMO_PERF_RECOVERY_2026-09-23.md. Nessuna modifica al codice/release DS41.

## Verifica ripetibile senza inferenza

```bash
cd /home/funboy/StrixHaloMimo26
PYTHONDONTWRITEBYTECODE=1 python3 scripts/mimo26/audit_perf_baseline_001.py --check
```

NEXT EXACT ACTION: consegnare REPORT.md / summary.json e commit di recupero, con i limiti sopra. Nessun nuovo job. Un solo esperimento futuro proposto, non eseguito: valutazione della qualità su compiti reali con originale come riferimento e protocollo dedicato. Non ricaricare A/B per riempire lacune storiche.
