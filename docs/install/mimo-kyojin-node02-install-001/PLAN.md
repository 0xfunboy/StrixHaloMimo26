# MIMO-KYOJIN-NODE02-INSTALL-001

## Copia operativa normalizzata del mandato allegato

**Fonte allegata:** `MIMO_KYOJIN_NODE02_INSTALL_001_PIANO_CODEX_2026-10-07(1).md`  
**SHA256 della fonte:** `dfa3fd8b936fc18c97e6ba8587e2408ff20c1b83d6f163b888cb442f85de7d83`  
**Data:** 7 ottobre 2026 — Europe/Rome.

Questa copia preserva decisione, limiti, sequenza e criteri del documento allegato. Il file allegato rimane l’autorità testuale; questa versione è conservata nel repository MiMo esistente per legare implementazione, evidenze e risultato.

## Risultato richiesto

Installare e lasciare utilizzabile su **NODE02 `02-EVO-X3`** un MiMo indipendente, raggiunto da NODE01 mediante `02-evo-x3-tb`. NODE01 conserva Gufo e HaloClu invariati e disponibili.

## Combinazione unica

| Componente | Pin |
|---|---|
| Pesi | `yamz-labs/MiMo-V2.6-Flash-MOPD-EXL3-Yamz` |
| Revisione | risolvere `f895a38` a SHA completo prima del download |
| Motore | `https://github.com/Yamz-Labs/kyojin.git` |
| Commit | `a3ac00d4a32148229e66c0916fcc3282bf47a3d9` |
| Accelerazione | DFlash, drafter EXL3 4 bpw incluso |
| Fedeltà | lossless attivo; nessuna tolleranza |
| Hardware | una Radeon 8060S/gfx1151 di NODE02, UMA 128 GB |
| Model ID | `mimo-mopd-kyojin` |
| API | `127.0.0.1:18571`, loopback NODE02 |
| Servizio | `mimo-kyojin.service`, unità utente separata e manuale |

## Directory

Deployment isolato su NODE02:

```text
/home/funboy/StrixHaloMimoKyojin
  .engine/kyojin-src/
  .venv/
  .python/
  bin/
  config/
  patches/
  docs/install/mimo-kyojin-node02-install-001/
```

Pesi e stato:

```text
/home/funboy/models/MiMo-V2.6-MOPD-EXL3-Yamz/<SHA_COMPLETO>/
/home/funboy/.local/state/strixhalomimokyojin/
/home/funboy/.cache/strixhalomimokyojin/
```

Il repository storico `/home/funboy/StrixHaloMimo26` resta separato. Su NODE01 è il repository specifico MiMo usato per coordinamento, client, documentazione e commit locale. Non viene clonato Qwen e non vengono importati vecchi collector.

## Preservazione NODE01

Non modificare o riavviare:

```text
qwen-gufo.service
qwen-gufo-workbench.service
Gufo API 127.0.0.1:18561/v1
HaloClu 127.0.0.1:18563/
```

Zero richieste Qwen. DS41 resta OFF. Vietati supervisor whole-pair, restore K2, `pair.sh on`, lifecycle di rank e modifiche al repository Qwen/HaloClu.

Su NODE01 sono ammessi soltanto letture, documentazione, client e inoltro SSH privato separato.

## Acquisizione

1. Verificare identità di NODE02 prima delle scritture.
2. Risolvere automaticamente il full SHA dei pesi.
3. Congelare manifest, dimensioni e hash.
4. Scaricare direttamente su NODE02 con resume e una sola destinazione.
5. Verificare:
   - 14 shard target EXL3;
   - `zz-e2e-step120.safetensors`;
   - directory `drafter/` completa;
   - tokenizer, template, config, indice, quantizzazione e licenze.
6. Non scaricare checkpoint Xiaomi originale, vecchi GGUF, altri bitrate, mmproj o un secondo drafter.
7. Conservare almeno 50 GiB liberi dopo download, ambiente, build e log.

## Runtime

- Python 3.12 gestito dentro il deployment.
- Venv dedicato.
- Torch AMD gfx1151 e ROCm SDK soltanto come pacchetti isolati.
- `EXL3_ROCM_SDK` e preload HSA del SDK secondo il pin Kyojin.
- Nessun aggiornamento globale di ROCm, kernel, driver, Mesa, BIOS o IOMMU.
- Build del commit fissato con architettura `gfx1151`.
- Test CPU/model-free e controllo GPU prima del caricamento dei pesi.

È ammesso soltanto un piccolo delta HTTP/observability che non tocchi modello, kernel, sampling o matematica. Ogni delta deve avere patch e SHA.

## Profili

```text
BASE: 40960 token
LONG: 196608 token candidato
```

BASE deve ospitare un input 32K con risposta e margine. LONG è ammesso soltanto dopo un piano memoria e mantenendo almeno 8 GiB `MemAvailable`.

## Serving

Avvio BASE previsto:

```text
python tools/mimo/serve.py \
  --host 127.0.0.1 --port 18571 \
  --model <MODEL_DIR> --model-id mimo-mopd-kyojin \
  --drafter <MODEL_DIR>/drafter \
  --ctx 40960 --dflash --ndt 7 \
  --dynamic-draft --draft-confidence 0.6 \
  --no-spec-gate --no-uncensor
```

Vincoli:

```text
EXL3_MIMO_LOSSLESS=1
EXL3_VERIFY_ATTN_LOOP=1
EXL3_VERIFY_GEMV_R=1
EXL3_DEC_MOE_UNION=1
EXL3_DEC_MOE_UNION_DEV=1
EXL3_ABLIT_RUNTIME=off
```

Il servizio resta manuale/statico; nessuna abilitazione al boot in questo mandato.

## Collaudo

BASE:

- identity e `/health`;
- `/v1/models`;
- risposta reale nonstreaming;
- SSE;
- cancellazione e drain;
- richiesta successiva dopo cancellazione;
- DFlash realmente caricato e contatori proposta/accettazione osservabili;
- confronto lossless DFlash/plain a temperatura 0;
- rendering del template e comportamento thinking effettivo;
- warmup e tre repliche limitate a circa 8K e 32K.

Thinking:

- non trasferire `reasoning_effort=high` da Qwen;
- verificare il template nativo;
- dichiarare esplicitamente se non esiste un livello HIGH distinto.

LONG:

- tentare 196608 soltanto dopo il gate memoria;
- se sostenibile, eseguire un lavoro sintetico di codice circa 64K e uno documentale circa 128K;
- altrimenti conservare BASE e dichiarare il limite, senza chiamarlo 128K qualificato.

## Budget

```text
Avvii MiMo massimi:          4
Richieste native massime:   18
Output token addebitati: 120000
MemAvailable minima:       8 GiB
```

Conservare un avvio per ripristinare BASE dopo il tentativo LONG. Nessun retry semantico, best-of o incremento opportunistico dei cap.

## Accesso privato

NODE02 ascolta soltanto su loopback. NODE01 può mantenere un forward utente separato:

```text
127.0.0.1:18571 NODE01 → 127.0.0.1:18571 NODE02
```

Dal PC Windows, usare SSH verso NODE01 e inoltrare la stessa porta. Verificare health, model ID e una richiesta attraverso l’intera catena.

## Consegna

Nel repository MiMo esistente e nel deployment NODE02 conservare:

```text
PLAN.md
source-lock.json
manifest e SHA256
ledger/checkpoint
RESULTS.json
REPORT.md
README_USO.md
raw ed evidenze essenziali
unità installate
client provato
rollback/stop verificato
commit locali, nessun push
```

Esito richiesto:

> MiMo è disponibile sul secondo Strix; questo è il collegamento; questo contesto funziona; questi sono i limiti osservati.
