# StrixHaloMimo26 — PERF-BASELINE-001

**Campagna:** prima baseline prestazionale riproducibile dopo la qualificazione di correttezza.

## Executive summary

- **A — mixed:** Baekpica `MQ-IQ2-XXS-XS-Q8-MM-BF16`, llama.cpp `58367713a6935c0810103378144008df32e3d5db`, 1× Strix Halo / ROCm0.
- **B — originale:** Xiaomi FP8/MXFP4, vLLM TP2 su 2× Strix Halo, backport QKV #57508.
- Entrambi i bracci: sanity preflight 6/6 PASS, sanity postflight 6/6 PASS, cache/prefix reuse disabilitato e verificato, cleanup PASS, K2 finale READY.
- Workload misurato: input esatti 512 e 2048 token, output 128 token, 3 repliche per lunghezza dopo warmup.

Questo è un confronto fra **configurazioni complete**: cambiano quantizzazione, runtime e numero di nodi. Nessun rapporto viene attribuito alla sola IQ2, alla sola rete o alla sola GPU.

## Stato terminale

- `CORRECTNESS_SANITY = PASS_BOTH_PRE_POST`
- `PERFORMANCE_MEASUREMENT_COMPLETE = PASS_WITH_A_CLIENT_TTFT_GAP`
- `METRICS_COMPARABLE = PARTIAL`
- `QUALITY_RETENTION_VS_ORIGINAL = NOT_EVALUATED`
- `LONG_CONTEXT = NOT_EVALUATED`
- `CONCURRENCY = NOT_EVALUATED`
- `MTP_DFLASH = NOT_EVALUATED`
- `K2_RESTORE = PASS_BOTH`

## Workload congelato

- 512 input token effettivi: ID SHA256 `493f138f2b4a01b1b265a43cfd0dd2e93019734628c42f971ddf5baca2c13468`.
- 2048 input token effettivi: ID SHA256 `a231a3eac529907d19c316a7cae51de6deedcb0dbbc4eea260e9bdfbbfecaa02`.
- Template/tokenizer identici; thinking OFF.
- Output target 128 token.
- Warmup escluso: 512, 2048.
- Ordine misurato: `512, 2048, 2048, 512, 512, 2048`.
- Sampling deterministico: temperature 0, seed 1.

## Risultato principale

| input | braccio | nodi | n valido | latenza richiesta mediana [min–max] | output end-to-end tok/s | rate post-primo-token | metrica prompt/first-token |
|---:|---|---:|---:|---:|---:|---:|---|
| 512 | A mixed | 1 | 3 | **10.143 [10.138–10.167] s** | **12.619 [12.590–12.625]** | **19.070 [19.064–19.107] tok/s** | prompt nativo 3482.3 ms; 147.029 tok/s; TTFT client N/A |
| 512 | B originale TP2 | 2 | 3 | **39.244 [39.194–39.335] s** | **3.262 [3.254–3.266]** | **3.417 [3.410–3.422] tok/s** | engine scheduled→first 2.082 [2.073–2.092] s; pure prefill N/A |
| 2048 | A mixed | 1 | 3 | **20.739 [20.733–20.760] s** | **6.172 [6.166–6.174]** | **18.990 [18.980–19.123] tok/s** | prompt nativo 14067.6 ms; 145.583 tok/s; TTFT client N/A |
| 2048 | B originale TP2 | 2 | 3 | **45.547 [45.525–45.969] s** | **2.810 [2.784–2.812]** | **3.417 [3.373–3.417] tok/s** | engine scheduled→first 8.356 [8.312–8.379] s; pure prefill N/A |

### Rapporti sulle metriche comparabili

| input | latenza B/A | output end-to-end A/B | post-primo-token A/B |
|---:|---:|---:|---:|
| 512 | **3.869×** | **3.869×** | **5.581×** |
| 2048 | **2.196×** | **2.196×** | **5.558×** |

Interpretazione:

- La latenza richiesta è confrontabile con cautela: A usa HTTP/SSE locale su NODE01; B usa una chiamata offline in-process vLLM su NODE01.
- Il rate post-primo-token ha la stessa semantica `(N-1)/intervallo post-first`, ma usa clock interni di runtime diversi.
- **TTFT non viene confrontato.** Il client TTFT di A non è recuperabile dal raw originario a causa di un bug dell'adapter sugli eventi `prompt_progress`; l'API offline di B non espone un TTFT client equivalente.
- **Prefill puro non viene confrontato.** A espone `prompt_ms`; B ha un tempo engine scheduled→first, non una misura semanticamente equivalente di pure prefill.

## Tutte le repliche — A mixed

| request | input | rep | output | latenza s | e2e tok/s | prompt ms | prompt tok/s | decode ms | post-first tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| measure-01-512-r1 | 512 | 1 | 128 | 10.167 | 12.590 | 3477.7 | 147.225 | 6661.8 | 19.064 |
| measure-04-512-r2 | 512 | 2 | 128 | 10.138 | 12.625 | 3490.6 | 146.681 | 6646.6 | 19.107 |
| measure-05-512-r3 | 512 | 3 | 128 | 10.143 | 12.619 | 3482.3 | 147.029 | 6659.6 | 19.070 |
| measure-02-2048-r1 | 2048 | 1 | 128 | 20.739 | 6.172 | 14050.3 | 145.762 | 6687.7 | 18.990 |
| measure-03-2048-r2 | 2048 | 2 | 128 | 20.760 | 6.166 | 14067.6 | 145.583 | 6691.1 | 18.980 |
| measure-06-2048-r3 | 2048 | 3 | 128 | 20.733 | 6.174 | 14090.6 | 145.345 | 6641.1 | 19.123 |

Cache reuse A: **0** per tutte le richieste (`timings.cache_n=0`, tutti i `prompt_progress.cache=0`, `prompt_n=tokens_evaluated=input length`).

## Tutte le repliche — B originale TP2

| request | input | rep | output | latenza s | e2e tok/s | engine sched→first s | engine post-first tok/s | cached input |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| measure-01-512-r1 | 512 | 1 | 128 | 39.194 | 3.266 | 2.082 | 3.422 | 0 |
| measure-04-512-r2 | 512 | 2 | 128 | 39.335 | 3.254 | 2.092 | 3.410 | 0 |
| measure-05-512-r3 | 512 | 3 | 128 | 39.244 | 3.262 | 2.073 | 3.417 | 0 |
| measure-02-2048-r1 | 2048 | 1 | 128 | 45.525 | 2.812 | 8.356 | 3.417 | 0 |
| measure-03-2048-r2 | 2048 | 2 | 128 | 45.547 | 2.810 | 8.379 | 3.417 | 0 |
| measure-06-2048-r3 | 2048 | 3 | 128 | 45.969 | 2.784 | 8.312 | 3.373 | 0 |

Ogni richiesta misurata di entrambi i bracci ha prodotto **esattamente 128 token di modello** e ha terminato sul limite configurato.

## Correzione adapter A

Il collector SSE originario contava il token placeholder `0` presente in ogni evento `prompt_progress` di questa build llama.cpp come se fosse output generato:

- 512 input: 4 progress event → 132 ID raw; terminale nativo `predicted_n=128`.
- 2048 input: 7 progress event → 135 ID raw; terminale nativo `predicted_n=128`.

La correzione post-hoc è deterministica e non modifica il run:

- il raw originale è conservato in `evidence/A-mixed/raw-source.jsonl`;
- viene rimosso un solo `0` iniziale per ciascun evento `prompt_progress` persistito;
- `tokens_predicted=128` e `predicted_n=128` confermano indipendentemente il conteggio;
- `cache_n=0`, `prompt_progress.cache=0`, `prompt_n=tokens_evaluated=input` confermano assenza di riuso prompt;
- latenza richiesta e timing nativi prompt/decode restano invariati;
- TTFT client e post-first client di A restano **N/A**, perché il vero timestamp del primo token non è ricostruibile dal vecchio raw.

L'adapter futuro è stato corretto e i self-test simulati passano; **il modello non è stato rilanciato solo per riempire una colonna mancante**.

## Memoria, swap, fault e telemetria leggera

| arm/node | MemAvailable mediana durante misure | process VmSwap mediana | GPU edge °C mediana [min–max] | socket W mediana [min–max] | gfx clock MHz mediana [min–max] |
|---|---:|---:|---:|---:|---:|
| A NODE01 | 36.006 GiB | 0.000 GiB | 63.0 [58.0–66.0] | 76.9 [72.1–79.3] | 2364 [2197–2444] |
| B NODE01 | 35.510 GiB | 0.818 GiB | 60.0 [58.0–62.0] | 77.5 [72.5–81.7] | 2678 [2570–2763] |
| B NODE02 | 36.522 GiB | 0.837 GiB | 61.5 [60.0–63.0] | 79.3 [76.5–82.0] | 2678 [2512–2767] |

Fault/I/O nelle richieste misurate:

- 512: A major fault/read bytes mediani 0/0; B NODE01 0/0; B NODE02 0/0.
- 2048: A 0/0; B NODE01 major fault mediana 2 (max 9), read bytes mediana 8192 (max 73728); B NODE02 major fault mediana 0 (max 7), read bytes mediana 0 (max 73728).

Su UMA non si sommano MemAvailable, RSS/PSS, GTT/device counters e pagine mappate: rappresentano memoria fisica sovrapposta. Il `VmSwap` dei processi vLLM viene riportato come contatore di processo (~0.82–0.84 GiB), non come prova di swap dei pesi del modello.

## Load diagnostico

- A mixed: **114.103 s**.
- B originale TP2: **279.734 s**.

I tempi di load non fanno parte delle sei repliche misurate.

## Correttezza e cleanup

- A sanity pre: PASS 6/6.
- A sanity post: PASS 6/6.
- B sanity pre: PASS 6/6.
- B sanity post: PASS 6/6.
- A cleanup / K2 restore: PASS / READY.
- B cleanup / K2 restore: PASS / READY.
- Nessun retry automatico o sweep di parametri è stato usato per ottenere numeri migliori.

## Cosa supporta questa campagna

Per **queste due configurazioni complete** e per questi workload 512/2048→128:

- la mixed single-Strix ha latenza richiesta nettamente inferiore e rate post-primo-token molto superiore all'originale TP2;
- il vantaggio end-to-end diminuisce al crescere del prompt perché prompt processing e decode pesano diversamente;
- il risultato non isola il contributo di IQ2, runtime llama.cpp, single-node execution, kernel o comunicazione TP2.

Non dimostra equivalenza di qualità della mixed rispetto all'originale. Non valuta long context, concorrenza, MTP/DFlash, Vulkan, PP2 o prontezza produzione.

## Prossimo esperimento suggerito — non eseguito

Usare l'originale come riferimento e fare una suite separata di capability/quality-retention su task reali contro la mixed. MTP/DFlash restano esclusi finché il loro loader path non viene qualificato separatamente.

## Artefatti

- `manifest.json` — bracci congelati e contratto metriche
- `workloads.json` — testo e ID token esatti
- `raw-results.jsonl` — warmup + richieste misurate canoniche
- `summary.json` — aggregati canonici
- `A-adapter-correction.json` — provenienza della correzione adapter
- `A-corrected-raw-results.jsonl` — derivato corretto A
- `evidence/A-mixed/`, `evidence/B-original/` — raw sorgente preservati
- `ERRATUM_CORRECTNESS_REPORT.md` — correzioni di rendicontazione della precedente iterazione
