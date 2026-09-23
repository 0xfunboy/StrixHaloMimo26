# StrixHaloMimo26 — PERF-BASELINE-001: audit dei risultati recuperati

**Conclusione: recupero completato; qualifica delle metriche PARZIALE.** Nessun modello è stato avviato e nessuna replica è stata ripetuta.

Verifica live: 2026-09-23T11:25:02.902002+02:00. Markdown e summary.json derivano dallo stesso insieme di 12 misure e 4 warmup, conservati separatamente.

## Configurazioni e provenienza

- A: Baekpica MQ-IQ2-XXS-XS-Q8-MM-BF16, revision b3794b22b6276f8120c340f52639f5eaa354a3fd; llama.cpp 58367713a6935c0810103378144008df32e3d5db; NODE01 HIP/gfx1151.
- B: Xiaomi MiMo-V2.6-Flash-RL, revision 5711b268169967567844e1e560e8a3966da959b1; vLLM 0.1.0rc2.dev9+g9255fd9fb9.rocm100; Torch 2.13.0+rocm10.0.0; NODE01+NODE02 TP2/PP1, eager, triton_unfused, KV 1 GiB/rank.
- Entrambi: context 4096, una sequenza, thinking/prefix reuse/MTP/DFlash OFF. Output naturale con cap 128, ignore_eos=false. A: batch 512 / ubatch 128, slot 1, GPU layers all, split none. Configurazioni effettive nei config.json dei run.
- I pin pesi sono quelli documentati nel mandato e nei percorsi/manifest esistenti; nessun nuovo hashing massivo o download. Binario A, patch e sorgente B sono stati confrontati con i relativi hash.

Workload SHA256: `905e3214673560903f60a396546e0e624f9851eccaea8c3cdd369924aecad5c6`. Le liste congelate contengono esattamente 512/2048 ID; i controlli runtime salvati attestano corrispondenza. Ordine comune: 512, 2048, 2048, 512, 512, 2048; warmup 512/2048 esclusi.

Il manifest delle 05:34 è posteriore ai run e NON è una preregistrazione. Config e frozen-SHA256SUMS delle finestre sono distinti dagli indici ricostruiti oggi. Il collector comune originale è stato recuperato dal peer con hash esatto; manca ancora la copia byte-identica dello script A, hash atteso `952c5583b5eda447862c9f803b2ecc14de6fc20a84e33bc16d03d6b2176a39c9`. Non è stata ricostruita per ipotesi.

## Risultati — mediana [min–max], tre repliche per cella

| Input→output | Braccio | n valido locale/native | Latenza osservatore locale (s) | Output/lat. locale (tok/s) | Decode engine dopo primo token (tok/s) |
|---|---|---:|---:|---:|---:|
| 512→128 | A | 3 | 10.143 [10.138–10.167] | 12.619 [12.590–12.625] | 19.070 [19.064–19.107] |
| 512→128 | B | 3 | 39.244 [39.194–39.335] | 3.262 [3.254–3.266] | 3.417 [3.410–3.422] |
| 2048→128 | A | 3 | 20.739 [20.733–20.760] | 6.172 [6.166–6.174] | 18.990 [18.980–19.123] |
| 2048→128 | B | 3 | 45.547 [45.525–45.969] | 2.810 [2.784–2.812] | 3.417 [3.373–3.417] |

**Confini distinti:** A cronometra HTTP/SSE fino all’evento terminale; B la chiamata offline LLM.generate fino al ritorno. Le latenze rimangono colonne etichettate per osservatore; i precedenti rapporti 3.87×/2.20× non sono promossi a confronto normalizzato fra client equivalenti.

Il decode engine usa `(128−1)/(ultimo−primo token)` all’interno di ciascun motore. La semantica llama è verificata nel sorgente pinned (n_gen_steps=n_gen−1; clock dopo sampling sincronizzato); quella B nei timestamp engine-core. Non sono ITL client né tempi puri dei kernel.
- 512: rapporto decode engine A/B **5.581×**.
- 2048: rapporto decode engine A/B **5.558×**.

## Prefill e TTFT: non equivalenti

| Input | Prompt nativo A, ms | Prompt nativo A, tok/s | B scheduled→first, s | TTFT client A/B |
|---:|---:|---:|---:|---|
| 512 | 3482.299 [3477.673–3490.563] | 147.029 [146.681–147.225] | 2.082 [2.073–2.092] | N/A / N/A |
| 2048 | 14067.623 [14050.349–14090.582] | 145.583 [145.345–145.762] | 8.356 [8.312–8.379] | N/A / N/A |

Il prompt time nativo A include il campionamento del primo token; non è il solo tempo dei kernel di prefill. Prompt time A e scheduled→first B non sono la stessa metrica; nessun rapporto prefill, nessun N_input/TTFT usato come prefill puro. Primo timestamp A contaminato dai progress event; B non aveva streaming client. n valido TTFT client=0.

## Tutte le richieste misurate

| Braccio / request ID | Input | Output modello | ID grezzi collector | Cache riusata | Latenza s | Decode engine tok/s |
|---|---:|---:|---:|---:|---:|---:|
| A / measure-01-512-r1 | 512 | 128 | 132 | 0 | 10.167147 | 19.063942 |
| A / measure-02-2048-r1 | 2048 | 128 | 135 | 0 | 20.739353 | 18.990203 |
| A / measure-03-2048-r2 | 2048 | 128 | 135 | 0 | 20.760424 | 18.980491 |
| A / measure-04-512-r2 | 512 | 128 | 132 | 0 | 10.138461 | 19.107462 |
| A / measure-05-512-r3 | 512 | 128 | 132 | 0 | 10.143138 | 19.070083 |
| A / measure-06-2048-r3 | 2048 | 128 | 135 | 0 | 20.733452 | 19.123289 |
| B / measure-01-512-r1 | 512 | 128 | 128 | 0 | 39.193761 | 3.422147 |
| B / measure-02-2048-r1 | 2048 | 128 | 128 | 0 | 45.525366 | 3.416824 |
| B / measure-03-2048-r2 | 2048 | 128 | 128 | 0 | 45.547293 | 3.416943 |
| B / measure-04-512-r2 | 512 | 128 | 128 | 0 | 39.334682 | 3.410116 |
| B / measure-05-512-r3 | 512 | 128 | 128 | 0 | 39.244469 | 3.416724 |
| B / measure-06-2048-r3 | 2048 | 128 | 128 | 0 | 45.969224 | 3.372603 |

Tutte le 12 completion sono conservate. A termina `limit`, B `length`, sempre 128 token reali. Nei raw A rimangono OVER_OUTPUT/cache_gate=false originali: il collector contava 4/7 zeri di progresso e interpretava male il contesto finale. Il derivato rimuove solo quel prefisso provato, verificando conteggi nativi, progress e prompt completo. Non sostituisce timestamp mancanti. I warmup hanno ID distinti e non entrano nelle statistiche.

## Memoria e risorse per nodo

| Braccio/nodo | MemAvailable GiB mediana [min–max] | VmSwap processo GiB | Major fault totali | Read bytes totali |
|---|---:|---:|---:|---:|
| A_NODE01 | 36.006 [35.934–36.153] | 0.000 [0.000–0.000] | 0 | 0 |
| B_NODE01 | 35.510 [35.462–35.574] | 0.818 [0.818–0.818] | 11 | 81920 |
| B_NODE02 | 36.522 [36.498–36.539] | 0.837 [0.837–0.837] | 7 | 73728 |

| Braccio/nodo | APU gfx °C | Gfx MHz | APU socket W |
|---|---:|---:|---:|
| A_NODE01 | 63.25 [58.75–66.88] | 2364 [2197–2444] | 76.91 [72.11–79.33] |
| B_NODE01 | 60.44 [58.38–62.12] | 2678 [2570–2763] | 77.50 [72.48–81.74] |
| B_NODE02 | 62.12 [60.62–63.62] | 2678 [2512–2767] | 79.28 [76.48–81.96] |

Sono 12 snapshot prima/dopo per nodo, non picchi o monitoraggio continuo. VmSwap B non è zero; piccole letture/fault sono conservate. Non si deduce che i pesi fossero su swap né l’assenza di qualunque collo di bottiglia. MemAvailable/RSS/PSS/GTT in UMA non si sommano. Throttling e assenza globale di altri workload durante la finestra non sono provati da questi soli snapshot.

## Sanity, serializzazione e restore

- A: `perf-baseline-001-A-mixed-001`, start 2026-09-23T03:10:59+0200; restore 2026-09-23T03:20:12+0200; un caricamento (114.103 s); sanity pre 6/6 e post 6/6, output salvati rivalidati CPU-only; cleanup PASS, K2 READY.
- B: `perf-baseline-001-B-original-001`, start 2026-09-23T03:21:32+0200; restore 2026-09-23T03:37:54+0200; un caricamento (279.734 s); sanity pre 6/6 e post 6/6, output salvati rivalidati CPU-only; cleanup PASS, K2 READY.

La fine del restore A precede l’inizio B. Le ricevute ripristinano K2 `dspark-k2-gfx1151`, release 5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513, non E1 storico. Il live riconciliato conserva l’epoch finale B 1790127186526215806; rank0/rank1/paired HTTP 200. Nessun processo MiMo riconosciuto dalla scansione e nessun lock pertinente risultano presenti. Le vecchie unità failed sono state preservate, non azzerate.

Il sanity A usava chat nonstreaming, non l’adapter SSE difettoso; questa qualifica riguarda i sei output naturali salvati, non una nuova validazione end-to-end del client streaming. I token ID completi del sanity performance non furono persistiti.

## Errata verificati e limiti residui

MemAvailable principale: 127883239424→39059042304 byte, delta 88824197120; 119.10054779052734→36.37656784057617 GiB, delta 82.72397994995117 GiB. Il valore 36.54961013793945 GiB appartiene al dopo-load della conferma (38325044 kB). Non è stata trovata la ricevuta per 119.33901977539062 GiB prima e 82.78940963745117 GiB delta: la precedente attribuzione certa alla stessa conferma è ritirata.

Le mediane 57.02004473880432 prompt / 20.24988356316951 decode appartengono esclusivamente alla conferma mixed-tp1-llama-sanity-001, build 97845c4f1. Non sono usate nella campagna attuale. Il report di correttezza originario resta preservato.

## Gate finali

- `CORRECTNESS_SANITY = PASS_BOTH_PRE_POST_OUTPUT_REVALIDATED`
- `PERFORMANCE_MEASUREMENT_COMPLETE = PARTIAL_12_OF_12_COMPLETIONS_RECOVERED_CLIENT_METRICS_MISSING`
- `METRICS_COMPARABLE = PARTIAL_ENGINE_DECODE_ONLY`
- `CACHE_VERIFIED = PASS_ALL_12_MEASURED`
- `SOURCE_FREEZE = PARTIAL_ORIGINAL_A_COLLECTOR_BYTES_NOT_FOUND`
- `QUALITY_RETENTION_VS_ORIGINAL = NOT_EVALUATED`
- `LONG_CONTEXT = NOT_EVALUATED`
- `CONCURRENCY = NOT_EVALUATED`
- `MTP_DFLASH = NOT_EVALUATED`
- `K2_RESTORE = PASS_BOTH_HISTORICAL_AND_LIVE`

## Artefatti e riproduzione CPU-only

- Canonici: `REPORT.md`, `summary.json`, `recovery-audit/normalized-results.jsonl`, `recovery-audit/audit.json`.
- Fonti originali: i due run sotto `/home/funboy/.local/state/strixhalomimo26/windows/`, con hash in `recovery-audit/source-SHA256SUMS` e copie preesistenti verificate.
- `raw-results.jsonl`, `arm-A-corrected.jsonl` e gli altri vecchi derivati rimangono intatti, come evidenza storica; non sono più la fonte del riepilogo corrente.
- Versioni precedenti dei report in `recovery-audit/prior-reports/`; collector comune recuperato in `recovery-audit/perf_measure_common.frozen.py`; stato live in `recovery-audit/live-reconciliation.json`.
- Verifica senza scrittura/inferenza: `python3 scripts/mimo26/audit_perf_baseline_001.py --check`.

## Un solo esperimento successivo proposto, non eseguito

Valutazione separata della qualità su compiti realistici, usando l’originale come riferimento e preregistrando validator e sorgenti completi prima di qualunque futura esecuzione.

Questo è un confronto delle configurazioni complete. Non isola la quantizzazione, i kernel, il numero di nodi o la comunicazione TP2; non prova qualità equivalente IQ2, long context, concorrenza o prontezza produzione.
