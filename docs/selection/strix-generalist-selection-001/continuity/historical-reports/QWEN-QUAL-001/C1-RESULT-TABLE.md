# C1 Qwen: risultati sui due Strix Halo

Riepilogo offline del 2026-09-06, solo raw gia raccolti. Nessuna richiesta modello, nuovo benchmark o modifica del piano/runtime. Mediane ricalcolate dalle risposte e dai tempi HTTP; validazione nativa e confronto offline rieseguiti senza HTTP: short PASS, long FAIL. Le summary storiche restano immutate.

**Miglior riferimento Qwen Q5 distribuito sostenibile da questa campagna C1: target-only, 18.6840 tok/s code e 18.6543 tok/s prosa.** Sono due workload separati, non una media generale. MTP3 raggiunge 31.3080 nel corto esatto, ma diverge nel lungo: non e promosso. Questo documento non dichiara un record assoluto fra tutti i modelli/quant storici.

## Configurazione comune

- Due EVO-X3 / Strix Halo gfx1151; llama.cpp HIP con **layer-RPC 22:78**, target su ROCm0 + RPC0. Non TP2; uso di entrambe le GPU non dimostra overlap utile o esecuzione simultanea dei due stage.
- Target originale `Qwen3.8-Flash-Next-UD-Q5_K_XL`, sei shard locali, **158286406650 byte su disco**. Non e una quant uniforme: layer0 routed up/gate Q5_K, routed down/shared/proiezioni Q8_0, router e altre componenti F32. Nessuna equivalenza di qualita con altre quant dedotta dal nome.
- Variante MTP: sidecar `mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf`, **2786568256 byte**, draft RPC0, `n_max=3`, `p_min=0.75`. Il target resta lo stesso.
- Context4096, batch/ubatch512, un solo slot, FA on, KV K/V Q8_0, threads4, load-mode none. Profilo server `reasoning_effort=xhigh` conservato; **le misure native raw sotto non applicano il template chat xhigh**.
- Payload misurato: native `/completion`, temperatura0, seed42, cache_prompt=false, ignore_eos=true, return_tokens=true, stream=false. Una warmup32 distinta esclusa, poi 2 ripetizioni short o 3 per categoria long. Cache del prompt fredda non implica pagine dei pesi fredde.

## Decode e HTTP: misure non strumentate

TPS decode = `(output_token_count-1)*1000/predicted_ms`; TPS HTTP = output_token_count/tempo HTTP. Le mediane delle due metriche sono calcolate separatamente, non trasformate l'una nell'altra. TTFT di queste richieste non-streaming: **non misurata**, anche per il lungo.

| Modalita / workload | Prompt / output / ctx | Ripetizioni | Mediana decode tok/s | TTFT | Mediana HTTP s | Mediana HTTP tok/s | Acceptance draft | Correttezza osservata |
|---|---|---:|---:|---|---:|---:|---|---|
| Target-only, short LRU | 97 / 64 / 4096 | 2 | 17.9207 | non misurata | 4.4490 | 14.4141 | n/a | 64 ID + testo, repeat esatto |
| MTP3, short LRU | 97 / 64 / 4096 | 2 | 31.3080 | non misurata | 2.8870 | 22.1826 | 45/46 =97.8261%, entrambe | repeat + stesso target esatti; PASS limitato al corto |
| Target-only, code | 44 / 256 / 4096 | 3 | **18.6840** | non misurata | 14.2339 | 17.9852 | n/a | 256 ID + testo, repeat3/3 esatto; riferimento lungo |
| MTP3, code | 44 / 256 / 4096 | 3 | 27.7743, **non qualificato** | non misurata | 9.8034 | 26.1135 | 160/182 =87.9121%, tutte3 | repeat3/3 PASS, target FAIL al token23 in tutte3 |
| Target-only, prosa | 27 / 256 / 4096 | 3 | **18.6543** | non misurata | 14.2348 | 17.9841 | n/a | 256 ID + testo, repeat3/3 esatto; riferimento lungo |
| MTP3, prosa | 27 / 256 / 4096 | 3 | 22.1508, **non qualificato** | non misurata | 12.1013 | 21.1547 | 130/159 =81.7610%, tutte3 | repeat3/3 PASS, target FAIL al token61 in tutte3 |

Indici mismatch zero-based. Il rapporto decode short e 1.7470x sullo stesso workload/build/modello; **non** si estende a code/prosa256. Nel verdetto lungo speedup qualificato e TPS MTP corretti sono `null`: sequenze divergenti non sono un'accelerazione equivalente al target. Nemmeno il target-only ha qui una certificazione generale di intelligenza o di tutti i contesti.

## TTFT e frontend/API: prove distinte

| Prova singola | Prompt / output effettivi | TTFT | HTTP end-to-end | Esito e limite |
|---|---|---|---|---|
| Target native SSE, code32 | 44 / 32, ctx4096 | **455.4903ms**, primo evento con token ID | 2.1898s; 14.6132 tok/s | 32/32 ID + testo esatti rispetto a target-repro32; decode osservato17.8763 tok/s. Non e una mediana ne TTFT del lungo. |
| MTP native SSE, LRU64 originale | 97 / 64, ctx4096 | **null, non ricostruibile** | durata/TPS HTTP null | Parser originale aspettava erroneamente `[DONE]`; native termina EOF dopo final. Raw rianalizzato PASS64, decode nativo31.3224 tok/s, acceptance45/46. Fallimento client originale conservato; niente tempi inventati. |
| Target API chat xhigh, `17*23` | usage78 / 67, inclusi token reasoning; limite512, ctx4096 | primo reasoning1053.5170ms; primo testo finale4594.5555ms | 4.7574s; rapporto usage/HTTP14.0833 tok/s, **solo smoke** | Alias corretto, reasoning preservato, risposta finale `391`, finish=stop e stream completo. Non e benchmark di intelligenza/TPS; non certifica il frontend MTP. |

L'API xhigh non e una rietichettatura delle completions greedy raw. La latenza al primo reasoning e quella al primo testo finale sono metriche diverse. Lo smoke non ha testato la cancellazione (`cancel_requested=false`).

## RAM e major fault: non sommare contatori UMA sovrapposti

Buffer modello dichiarati al caricamento: target NODE01 ROCm0 **22.0696GiB**, NODE02 RPC0 **74.0427GiB**; NODE01 CPU_Mapped **50.6642GiB** e ROCm_Host0.6290GiB. Con MTP si aggiunge draft RPC0 **2.5850GiB**. CPU_Mapped e un mapping lazy, non prova che tutta quella memoria sia residente. Non sommare RSS + GTT + mapped come RAM indipendente.

Ogni riga seguente copre l'intera finestra telemetrica, **warmup compresa**, non soltanto il decode misurato. Valori NODE01 / NODE02; GiB=2^30 byte.

| Finestra | Campioni | Peak RSS processi GiB | Min MemAvailable GiB | Peak GTT device GiB | Delta major fault processi | VmSwap processi |
|---|---:|---|---|---|---|---|
| Target short | 10 | 1.7651 /0.5736 | 94.6631 /44.1707 | 22.6631 /75.0317 | +2329 /+245 | 0 /0 |
| MTP short | 7 | 1.9040 /0.5797 | 94.2432 /41.1022 | 22.7464 /77.9869 | +60 /0 | 0 /0 |
| Target long, code+prosa | 77 | 2.2477 /0.5770 | 94.0240 /43.8417 | 22.6530 /75.0220 | +7952 /0 | 0 /0 |
| MTP long, code+prosa | 60 | 2.6099 /0.5803 | 93.6881 /41.1656 | 22.7468 /77.9990 | +8574 /0 | 0 /0 |

Niente claim "zero major fault". Nel profilo MTP lungo i fault arrivano in due ondate sui primi workload; restano piatti nei campioni interni alle successive ripetizioni. Memoria disponibile ampia e VmSwap0 non provano assenza di I/O file-backed; VmSwap0 dei processi non significa swap di sistema vuoto. Non e disponibile un'attribuzione causale dei fault a un preciso tensore PLE. GTT/busy sono dell'intero device, non esclusivi della richiesta.

## Cosa spiega il profilo, e cosa no

`C1-LIGHT-PROFILE.md/.json` ricostruisce `draft()` host: circa1.143-1.152s per code256 e1.286-1.299s per prosa256. Questo timer **non include tutto il catch-up MTP**, ne separa GPU/verify/TCP/snapshot. Non ricavare un Amdahl bound o una promessa depth6 dai suoi residui. GPU busy campionato MTP lungo NODE01 0-19%, NODE02 1-67% non misura overlap. Le prime misure sono piu lente, ma anche quelle calde restano circa27.8/22.2 tok/s e divergono dal target.

Il riproduttore coldcode32 e i replay strumentati sono **diagnostica, mai performance**. L'eventuale localizzazione/fix successivo necessita di nuovi gate; non rende retroattivamente qualificati questi numeri C1.

## GLM: fallback storico separato

GLM-5.3-Flash CIRU IU4, TP2+DFlash2, preset qualificato **24.851 tok/s**: riferimento preservato, non il "miglior Qwen" e non confronto diretto a stessa qualita/workload/tokenizer. Prove storiche: `/home/funboy/ai-exp/reports/moe-cluster/CIRU-TP2-001/dflash5-f1-wmma-003/benchmark/{protocol.json,raw.jsonl,summary.json}`, `quality/`, `api-smoke-fixed/`, `promotion-1788669299103203042.json`. Il presente report non afferma che quel servizio sia attualmente attivo durante la diagnostica Qwen.

## Indice raw riproducibile

Root assoluta comune **`/home/funboy/ai-exp/reports/moe-cluster/QWEN-QUAL-001/`**. I nomi seguenti sono relativi a questa root; ogni directory misurata contiene `protocol.json`, `warmup-{request,response,result}.json`, `{code,prose}-N-{request,response,result}.json` per le categorie presenti, `summary.json`, `live-attestation.json`.

- `c1-target-short/`, `c1-mtp-short/`: 2xLRU64; `c1-mtp-short/reference.json` collega il target esatto.
- `c1-target-measure/`, `c1-mtp-measure/`: 3xcode256 +3xprosa256; **`c1-long-crossmode-verdict.json`** e il verdetto conclusivo ricalcolato, senza riscrivere la vecchia summary MTP `NOT_EVALUATED`.
- Per ciascuna delle quattro directory: file adiacenti `NOME-identity.json`, `NOME-telemetry.jsonl`. Contengono closure runtime, SHA ricevute dei pesi/stat, comandi/PID/InvocationID e campioni memoria. Le attestazioni salvate non sono una retroverifica live di processi storici.
- `corpus/existing-native.jsonl`, `corpus/existing-native-manifest.json`: prompt e provenienza; short LRU usa il prompt storico nel proprio request.
- `c1-target-repro32/`, `c1-target-repro32-identity.json`, `c1-target-repro32-telemetry.jsonl`: riferimento specifico code32 per SSE e riproduzione, non sostituisce il target lungo.
- `c1-target-sse/{protocol.json,request.json,raw.sse,events.jsonl,events.json,final-event.json,response.json,summary.json}`.
- `c1-mtp-sse/{protocol.json,request.json,raw.sse,summary.json,offline-reanalysis.json}`: originale fallito e rianalisi conservati entrambi.
- `c1-target-api/{models.json,answer-request.json,answer.sse,answer-events.json,answer-response.json,summary.json}`.
- `C1-LIGHT-PROFILE.md`, `C1-LIGHT-PROFILE.json`; `c1-target-evidence/`, `c1-target-long-evidence/`, `c1-mtp-evidence/` con journal/unit per API e RPC. Filtrare il PID della specifica identity: i journal contengono anche caricamenti precedenti.
- `c1-cache-branch/`: A/B/A32 cached, separato dal decode cold; output PASS non dimostra da solo il ripristino dello stato hidden del drafter.
- `replay44-requests/`: due coldcode32 diagnostiche riproducono mismatch23, nessuna cattura M4 alla posizione presunta44; nessun numero di performance da promuovere.
- Modelli: `/home/funboy/models/gguf/qwen3.8-flash-next-unsloth-q5-k-xl/` e `/home/funboy/models/gguf/qwen3.8-flash-next-mtp-unsloth-shared-q8/`; configurazione e runtime: `/home/funboy/ai-exp/strix-moe-cluster/config/models.lock.json`, `runtime/qwen-upstream-source/`, `runtime/qwen-upstream-build/`. Snapshot C1 pre-diagnostica: `c1-bin/` sotto la root raw.
