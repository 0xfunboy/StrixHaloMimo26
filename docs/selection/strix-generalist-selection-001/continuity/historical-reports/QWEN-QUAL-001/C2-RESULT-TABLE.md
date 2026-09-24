# C2 Qwen: risultati finali, non promosso

Ricalcolo offline del 2026-09-06 dai raw completati. **MTP3 passa code/prosa64, ma fallisce il primo code256 al token146 (zero-based).** Il lungo si arresta qui: nessun repeat MTP256, nessuna prosa MTP256. `25.698125 tok/s` e una sola osservazione non qualificata, **non una mediana**. Nessuna richiesta HTTP, servizio o piano modificato da questo audit.

## Configurazione e perimetro

- Due Strix Halo gfx1151, HIP **layer-RPC 22:78**, ROCm0 + RPC0: non TP2, nessuna dimostrazione di overlap dei due nodi.
- Qwen3.8-Flash-Next **UD-Q5_K_XL**, sei shard originali, 158286406650 byte su disco; MTP condiviso Q8_0, 2786568256 byte, draft su RPC0, massimo3 token, p_min0.75. Dimensioni disco, non RAM residente; quant non uniforme, nessuna equivalenza di intelligenza dedotta dal nome.
- Context4096, batch/ubatch512, un solo slot, FA on, K/V Q8_0, threads4, load-mode none. C2 attiva `GGML_CUDA_QWEN_Q8_KV_VEC4=1` sia nel target di riferimento sia nel candidato MTP.
- Payload native `/completion`: temperatura0, seed42, cache_prompt=false, ignore_eos=true, return_tokens=true, stream=false. Warmup32 separata esclusa dalle mediane. Profilo server xhigh conservato, ma **queste completions non applicano il template chat xhigh**.
- Le quattro identity C2 hanno uguali mappe SHA runtime/pesi, weight-stat e parametri target. Ricevute SHA dei pesi riutilizzate: nessun hash integrale dei checkpoint eseguito in questo audit.

## Misure C2

Decode TPS ricalcolati come `(N-1)*1000/predicted_ms`; HTTP TPS come `N/http_wall_s`. Le mediane delle metriche sono calcolate separatamente. **TTFT e smoke frontend/chat/API C2 non misurati/eseguiti**; la riuscita della completion nativa non sostituisce quei test. Nessuna certificazione generale di qualita o logits completi.

| Modalita / workload | Prompt / output / ctx | Run | Decode tok/s | HTTP s | HTTP tok/s | Acceptance | Correttezza |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| Target short code | 44 / 64 / 4096 | 2 | mediana17.6403 | mediana4.1662 | mediana15.3623 | n/a | repeat esatto |
| MTP3 short code | 44 / 64 / 4096 | 2 | mediana26.6334 | mediana2.9866 | mediana21.4295 | 37/40=92.5000%, entrambe | ID e testo esatti rispetto al target C2; repeat esatto |
| Target short prosa | 27 / 64 / 4096 | 2 | mediana17.5390 | mediana4.1103 | mediana15.5714 | n/a | repeat esatto |
| MTP3 short prosa | 27 / 64 / 4096 | 2 | mediana23.3886 | mediana3.2059 | mediana19.9714 | 38/48=79.1667%, entrambe | ID e testo esatti rispetto al target C2; repeat esatto |
| Target long code | 44 / 256 / 4096 | 3 | mediana18.2492 | mediana14.5615 | mediana17.5806 | n/a | repeat3/3 esatto, riferimento C2 |
| Target long prosa | 27 / 256 / 4096 | 3 | mediana18.2005 | mediana14.5826 | mediana17.5552 | n/a | repeat3/3 esatto, riferimento C2 |
| MTP3 long code | 44 / 256 / 4096 | **1** | **singolo25.698125, non qualificato** | singolo10.630182 | singolo24.082371 | 159/177=89.8305% | **FAIL token146; repeat NON TESTATO** |
| MTP3 long prosa | non eseguita | **0** | non misurato | non misurato | non misurato | n/a | NON TESTATA |

Verifica offline indipendente: payload uguali tra le modalita C2; tutti gli 8 confronti short (2 candidati x2 target, per workload) hanno ID e testo esatti. L'unico MTP code256 diverge al token146 contro tutte3 le risposte target C2. Mediana MTP lunga qualificata e speedup lungo qualificato: **null**. I campi aggregati `repeat_status=FAIL` della summary lunga non significano che una seconda esecuzione abbia fallito: **non e stata fatta**.

## Confronto con C1 e fallback GLM

| Riferimento storico | Decode tok/s | Esito / limite del confronto |
| --- | --- | --- |
| C1 target code256 / prosa256 | mediane18.6840 /18.6543 | repeat3/3; precedente riferimento Qwen, runtime diverso |
| C1 MTP3 code256 / prosa256 | mediane27.7743 /22.1508, non qualificate | FAIL rispetto al target ai token23 /61, non preset promossi |
| C1 MTP3 LRU64 | mediana31.3080 | corto esatto, **prompt97 diverso** dai code/prosa64 C2: non confronto diretto |
| GLM-5.3-Flash CIRU IU4 TP2+DFlash2 | **storico24.851** | fallback qualificato preservato; non misurato adesso, nessuna inferenza sul servizio attivo o equivalenza di qualita/tokenizer/workload |

**C2 non preserva globalmente la sequenza del target C1.** Anche il target-only checkpointa il prompt prima degli ultimi4 token, quindi la nuova aritmetica FA viene usata nel prefill. A payload256 identico, C2 target differisce da C1 target al token78 code /61 prosa. La fedelta MTP C2 va confrontata con il **target della stessa build C2**, come fatto qui; cio non rende equivalenti i numeri C1/C2. Dettaglio e journal in `C2-TARGET-REGRESSION.md`; storico completo in `C1-RESULT-TABLE.md`.

## RAM e major fault

Finestre telemetriche complete, **warmup inclusa**, non attribuzione per singola richiesta o solo decode. GiB=2^30 byte; ogni coppia e NODE01 / NODE02. Identita PID/starttime verificate costanti dentro ogni finestra. RSS e GTT si sovrappongono su UMA: **non sommarli**, ne sommare il mapping lazy PLE come ulteriore RAM residente.

| Finestra | Campioni / durata | Peak RSS processi GiB | Min MemAvailable GiB | Peak GTT device GiB | Delta major fault processi |
| --- | --- | --- | --- | --- | --- |
| C2 target short, code+prosa | 17 /18.5306s | 2.2173 /0.5820 | 94.1146 /43.7970 | 22.6521 /74.9806 | +2115 /+0 |
| C2 target long, code+prosa | 78 /89.3886s | 2.2451 /0.5827 | 93.9770 /44.2729 | 22.6521 /74.9806 | +5321 /+0 |
| C2 MTP short, code+prosa | 13 /13.9065s | 2.3470 /0.5851 | 93.5961 /40.9934 | 22.7335 /77.9307 | +157 /+2 |
| C2 MTP long, solo warmup+code1 | 11 /11.5909s | 2.3470 /0.5859 | 93.7782 /41.0861 | 22.7350 /77.9369 | +786 /+0 |

VmSwap dei processi rimane0 in tutti i campioni, **non** significa swap di sistema vuoto o zero I/O file-backed. GTT/busy sono contatori dell'intero device. I fault sono differenze primo-ultimo campione della finestra, non comprendono il precedente caricamento e non sono attribuiti causalmente a uno specifico tensore. Non dichiarare zero major fault o dedurre overlap dai campioni GPU.

## Raw e identita verificabili

Root comune: `/home/funboy/ai-exp/reports/moe-cluster/QWEN-QUAL-001/`.

- `c2-target-short/`, `c2-target-measure/`, `c2-mtp-short/`, `c2-mtp-measure/`: `protocol.json`, `summary.json`, `live-attestation.json`, `warmup-{request,response,result}.json` e i `{code,prose}-N-{request,response,result}.json` effettivamente presenti. Il lungo MTP contiene solo warmup e code1; nessun raw di prosa o repeat va inventato.
- Per ciascuna directory, file adiacenti `NOME-identity.json` e `NOME-telemetry.jsonl`. SHA256 identity target short/long: `8b452bff47b0f0c77d50f2b45b27cc8012732b700a89097bb617c6d896e13741`; MTP short/long: `97da65b97fc4cc7e83d68eaac858940aff719434cb0b547e0b898afef8464785`.
- Target PID1424153 / RPC1608462, owner `42ec2fe877c7bbd0da0cae252befb907`; MTP PID1429509 / RPC1625905, owner `d7d5f156209e03a7401a3bbf79714c3d`. Sono identita **dei run registrati**, non attestazione di processi attualmente attivi.
- `c2-mtp-measure/summary.json` SHA256 `5d7d5e49c1f8da7e4f6a0c8950200f5c8b2afb69af77c58747163af26465f99a`: conserva arresto al primo mismatch e `NOT_PROMOTED`.
- `C2-TARGET-REGRESSION.md`, `C1-RESULT-TABLE.md`, `C2-FA-VEC4-PREREGISTER.md`: regressione cross-versione, storico e criteri pre-registrati. La correzione locale FA non qualifica retroattivamente l'intero modello.
- GLM storico: `/home/funboy/ai-exp/reports/moe-cluster/CIRU-TP2-001/dflash5-f1-wmma-003/benchmark/{protocol.json,raw.jsonl,summary.json}`, `quality/`, `api-smoke-fixed/`, `promotion-1788669299103203042.json`.

Nessun nuovo benchmark e nessuna modifica a PLAN, README o servizi sono autorizzati o eseguiti da questa tabella.
