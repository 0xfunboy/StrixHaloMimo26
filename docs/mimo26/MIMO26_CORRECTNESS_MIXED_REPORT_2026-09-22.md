# StrixHaloMimo26 — qualificazione QKV originale + mixed GGUF

**Data:** 2026-09-22
**Stato finale:** PASS sui gate di correttezza previsti da questa iterazione.
**Hardware:** esclusivamente 2× Strix Halo; nessuna RTX 3090 / CUDA.

## Executive summary

Questa iterazione ha chiuso i due problemi prioritari:

1. **Checkpoint originale Xiaomi su 2× Strix Halo:** il loader fused-QKV precedente era errato. Il backport della logica vLLM PR #57508, con checkpoint export `ckpt_tp=4`, passa fixture indipendenti TP1/TP2/TP4 su full-attention e SWA e produce output corretto end-to-end in TP2.
2. **Mixed GGUF Baekpica su un solo Strix:** download e SHA256 completi; i quattro shard principali vengono caricati da llama.cpp su una sola Radeon 8060S / gfx1151 e superano il sanity set testuale.

Non è stata eseguita una nuova campagna prestazionale. I numeri di timing presenti sotto sono misure diagnostiche dei sanity run, non benchmark qualificati 512/2048×3.

---

## 1. Recupero r6

Run storico: `tp2-eager-triton-r6-qkv-global`
Invocation: `4f5cd34e04ed4fe8a07fb9dd738eab98`

Risultato ricostruito:

- MODEL_LOAD: **PASS**
- 65/65 shard caricati;
- modello: **79.44 GiB/rank**;
- KV cache: 1 GiB/rank;
- QUALITY: **NOT_EVALUATED**
- RUN_COMPLETION: **FAIL harness**
- causa: il vecchio harness passava `prompt_token_ids` in una forma che questa build vLLM interpretava con chiavi stringa; il crash avveniva in input validation prima della prima inferenza;
- K2 restore: **PASS**.

R6 quindi non qualifica né invalida la QKV.

Evidence: `docs/mimo26/evidence/r6-20260922/`.

---

## 2. Ricostruzione r7

Run: `tp2-eager-triton-r7-upstream57508`
Wrapper InvocationID: `cc3cca8e2002480d8a636ad12b7f1ae9`

### Timeline osservata

- 15:25:00 — wrapper active;
- 15:25:10 — K2 OFF;
- 15:25:11 / 15:25:13 — rank1 / rank0 MiMo avviati;
- 15:29:43 — rank0 weights load completo, 255.18 s;
- 15:29:48 — rank0 model load completo, 79.44 GiB;
- 15:29:58 — KV cache pronta;
- 15:30:00 — engine init completo;
- 15:35:09.989 — systemd inizia a fermare il wrapper;
- 15:35:10 — rank1 segnala il collective interrotto / remote process exited;
- 15:35:10 — wrapper entra in RESTORE con rc=143;
- 15:35:20 — restart K2 iniziato;
- 15:36:39.995 — il wrapper supera `TimeoutStopSec=90s` durante cleanup e viene SIGKILLato.

Proprietà reali wrapper:

- Type: simple
- RuntimeMaxSec: **3h**
- TimeoutStartSec: 90s
- TimeoutStopSec: 90s
- KillMode: control-group
- Result finale systemd: timeout
- ExecMainStatus: 9/KILL

**Conclusione r7:** `CAUSE_UNDETERMINED_EXTERNAL_STOP_OBSERVED`.

Il RuntimeMaxSec da 3 ore non era scaduto. Il primo evento control-plane osservabile è l'inizio dello stop dell'unità wrapper; i journal disponibili non identificano il caller che lo ha richiesto. Il successivo `Result=timeout` descrive il timeout del cleanup, non la causa iniziale.

Evidence: `docs/mimo26/evidence/r7-upstream57508/r7-timeline.json`.

---

## 3. Runner supervisionato

È stato introdotto un runner separato con:

- run ID non riutilizzabile;
- lock per run;
- compute lock cluster;
- eventi JSONL progressivi;
- `load.json` e `quality.json` atomici;
- causa iniziale distinta dal cleanup;
- worker RuntimeMax e work timeout separati;
- `ExecStopPost` systemd per cleanup anche dopo interruzione del coordinatore;
- restore K2 idempotente con controller esistente;
- nessuna dipendenza esclusiva dal trap Bash.

### Self-test CPU senza K2 reale

PASS per:

- completamento normale;
- worker exit 7;
- work timeout;
- SIGTERM del coordinatore;
- qualità mancante resta NOT_EVALUATED;
- cleanup non sovrascrive la causa iniziale;
- readback non rilancia il run;
- cleanup idempotente;
- nessun dummy worker/lock residuo.

Smoke del runner reale `runner-smoke-003`: PASS con rank0/rank1 dummy, quality persistita prima del teardown e cleanup PASS.

Evidence: `docs/mimo26/evidence/runner-selftest/report.json`.

---

## 4. Loader QKV — backport vLLM #57508

Reference:

- PR: vLLM #57508
- merge commit: `211e252d0b4f8429f9b15fc52bdfed07782c7f70`
- patch upstream salvata in evidence;
- riscontro V2.6 DGX salvato separatamente.

La build vLLM installata è precedente al fix e assumeva una disposizione errata. Il checkpoint MiMo-V2.6 Flash usa quattro chunk di export:

`[Q_c | K_c | V_c] × 4`

con scale FP8 per-chunk. Anche gli SWA layer con 8 KV head restano esportati con `ckpt_tp=4`.

Patch locale:

`benchmarks/mimo26/vllm_patch.py`

SHA256:

`eeb66fefbf1b63459e5712c031399f2d24d9ac05956c97b4e979ad03b901be72`

Hash identico importato su NODE01 e NODE02.

### Fixture indipendenti

Copertura:

- full attention;
- SWA;
- TP=1, TP=2, TP=4;
- sintetico con chunk/scale costruiti indipendentemente;
- tensor reali del checkpoint;
- negative regression contro la precedente patch global-QKV.

Risultati checkpoint reale:

**Full attention**

- TP2 rank0 rel-L2: 0.0104553
- TP2 rank1 rel-L2: 0.0069001
- TP4: bit-exact su tutti i rank

**SWA**

- TP2 rank0 rel-L2: 4.43e-8
- TP2 rank1 rel-L2: 4.24e-8
- TP4: bit-exact su tutti i rank

Vecchia interpretazione global-QKV, SWA TP2:

- rank0 rel-L2: **0.7581**
- rank1 rel-L2: **0.1487**

La regression negativa intercetta quindi nettamente la patch precedente.

**Loader QKV: PASS.**

Nota: l'MTP loader installato è ancora pre-#57508; speculative decoding è rimasto OFF e non è qualificato da questa iterazione.

---

## 5. Originale Xiaomi — TP2 correctness run

Run autorevole:

`orig-tp2-qkv57508-sanity-001`

Configurazione:

- NODE01 + NODE02;
- TP2 / PP1;
- text-only;
- eager;
- context 4096;
- KV cache 1 GiB/rank;
- `triton_unfused` per MoE MXFP4;
- prefix cache OFF;
- thinking OFF;
- MTP OFF;
- DFlash OFF;
- performance campaign OFF.

### Load

- status: **PASS**
- load_s: **277.716 s**
- model memory osservata dai log: **79.44 GiB/rank**
- KV cache: **1 GiB/rank**
- worker exit: 0 / 0

### Sanity quality

**6/6 PASS**

| Test | Output |
|---|---|
| aritmetica | `323` |
| estrazione | `ZEBRA-4821` |
| JSON | `{"alpha": 7, "beta": "blue"}` |
| comprensione IT | `Cobalto` |
| comprensione EN | `Bob` |
| codice | funzione `clamp` valida; unit-test sandbox PASS |

Tutti i casi hanno `finish_reason=stop`.

I token ID di prompt e output sono persistiti in `quality.json`.

**Originale TP2: END-TO-END CORRECTNESS PASS sul sanity set.**

TTFT/prefill/decode: **NON MISURATI come benchmark**, intenzionalmente in questa iterazione.

Cleanup finale originale:

- worker MiMo: terminali;
- K2 restore: PASS;
- K2 finale: READY.

---

## 6. Mixed GGUF — download e integrità

Repository:

`Baekpica/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF`

Revision congelata:

`b3794b22b6276f8120c340f52639f5eaa354a3fd`

Variante:

`MQ-IQ2-XXS-XS-Q8-MM-BF16`

Download verificato completo:

- 4 shard main model;
- mmproj BF16;
- DFlash Q8_0;
- SHA256 di ogni peso = manifest upstream.

Main tensor payload dal manifest:

`88,771,782,144 bytes`

Tutti i weight file della variante:

`93,092,184,576 bytes`

Tensor types main GGUF:

- F32: 248
- Q8_0: 119
- IQ2_XS: 47
- IQ2_XXS: 94

Metadata:

- architecture: `mimo2`
- split count: 4
- tensor count: 508
- blocks: 51
- context metadata: 1,048,576
- embedding: 4096
- attention heads: 64
- KV head pattern: 4/8 coerente col modello

La build llama.cpp locale:

- build 11098
- commit `97845c4f1ffae096d22ad772df396550f9f78306`
- gfx1151 HIP
- contiene MIMO2 e tutti i tensor type usati.

Il commit llama.cpp pin-nato dalla ricetta mixed:

`58367713a6935c0810103378144008df32e3d5db`

è un **antenato** della build locale.

---

## 7. Comparabilità revisioni

Originale locale:

`5711b268169967567844e1e560e8a3966da959b1`

Source revision dichiarata dalla mixed:

`3b38d063180c3e4aed9691fdc735f3d10b266ee4`

Gli SHA dei contenuti verificati però coincidono:

- 67/67 weight file safetensors: stesso LFS SHA256;
- weight cambiati: 0;
- config.json: identico;
- generation_config.json: identico;
- tokenizer.json: identico;
- tokenizer_config.json: identico;
- chat_template.jinja: identico;
- modeling_mimo_v2.py: identico.

**Comparabilità del text path: VERIFIED** per i file controllati. Le revision ID Git/HF sono diverse, ma i pesi e i principali file text-runtime verificati sono identici.

---

## 8. Mixed GGUF — singolo Strix

### Run autorevole, sanity completo

Run: `mixed-single-correctness-002`

Nodo: `01-EVO-X3` soltanto.

Runtime:

- llama.cpp commit **esattamente pin-nato dalla ricetta mixed**: `58367713a6935c0810103378144008df32e3d5db`;
- HIP/gfx1151, device `ROCm0`;
- solo i quattro shard main model;
- context 4096;
- parallel/slot: 1;
- `--n-gpu-layers all`, split-mode none;
- reasoning/thinking OFF;
- nessun mmproj, DFlash o MTP/speculative attivo;
- nessun offload SSD intenzionale;
- process VmSwap: 0 kB.

Load:

- status: **PASS**
- load_s: **102.096 s**
- MemAvailable prima: 127,883,239,424 bytes
- MemAvailable dopo load: 39,059,042,304 bytes
- delta MemAvailable: 88,824,197,120 bytes (~82.73 GiB)
- cleanup K2: PASS / READY

Non si sommano RSS/PSS e MemAvailable perché Strix Halo usa UMA.

Sanity quality: **6/6 PASS**, cioè lo stesso set dell'originale:

| Test | Output |
|---|---|
| aritmetica | `323` |
| estrazione | `ZEBRA-4821` |
| JSON | `{"alpha": 7, "beta": "blue"}` |
| comprensione IT | `Cobalto` |
| comprensione EN | `Bob` |
| codice | funzione `clamp` valida; unit-test gate PASS |

Tutti i casi hanno `finish_reason=stop`.

### Conferma indipendente sulla build locale più recente

Run: `mixed-tp1-llama-sanity-001`

Runtime llama.cpp: `97845c4f1ffae096d22ad772df396550f9f78306`

- load PASS, 110.117 s;
- 5/5 sanity test eseguiti: PASS;
- MemAvailable dopo load ~36.55 GiB;
- process VmSwap 0;
- cleanup K2 PASS.

Su queste sole richieste corte llama-server ha riportato:

- prompt throughput mediano diagnostico: **~57.02 tok/s**
- decode throughput mediano diagnostico: **~20.25 tok/s**

Questi valori sono diagnostici e **NON costituiscono il benchmark qualificato 512/2048 × 3**.

I blocchi MTP 48–50 presenti nel GGUF sono stati segnalati come inutilizzati/ignorati con speculative decoding OFF; il GGUF non è stato modificato.

**Mixed single-Strix: LOAD PASS + FULL SANITY QUALITY PASS.**

## 9. Stato finale cluster

Alla fine di entrambe le finestre:

- K2 preset: `dspark-k2-gfx1151`
- K2 state: **READY**
- rank0 HTTP: 200
- rank1 HTTP: 200
- paired backend HTTP: 200
- processi MiMo modello residui: **nessuno**
- compute lock MiMo residuo: **nessuno**
- RTX 3090 / CUDA: **non usati**
- kernel/ROCm/USB4/rete: **non modificati**
- release DS41: **non modificata**

---

## 10. Decisione

Entrambi i percorsi sono ora tecnicamente utilizzabili sul sanity set:

1. **Originale FP8/MXFP4, 2× Strix, TP2:** corretto dopo backport #57508.
2. **Mixed IQ2/Q8, 1× Strix:** corretto sul sanity set e residente con ~36.5 GiB MemAvailable dopo load.

Il prossimo esperimento motivato dalle misure è una campagna prestazionale separata e congelata:

- workload 512 e 2048 prompt token;
- output 128;
- 3 ripetizioni dopo warmup;
- TTFT/prefill/decode separati;
- prima mixed singolo nodo;
- poi originale TP2 sullo stesso workload;
- misurare il costo collective prima di valutare TP1/PP2;
- HIP vs Vulkan solo dopo baseline mixed;
- MTP/DFlash solo dopo baseline non-speculative.

Il vecchio numero r5 da 3.3036 tok/s **non è una baseline valida** e non viene usato nel confronto.
