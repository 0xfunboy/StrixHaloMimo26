# MIMO-KYOJIN-NODE02-INSTALL-001 — rapporto finale

**Esito:** `COMPLETE_BASE_READY_LONG_BLOCKED_MEMORY_GUARD`  
**Accesso da NODE01:** `http://127.0.0.1:18571/v1`  
**Model ID:** `mimo-mopd-kyojin`

## Risultato operativo

MiMo è installato e disponibile sul secondo Strix con profilo **BASE 40960**, DFlash e verifica lossless attivi. NODE02 ascolta soltanto sul loopback; NODE01 mantiene un forward SSH privato separato. Gufo e HaloClu su NODE01 non sono stati riavviati o modificati.

## Identità congelate

```text
Nodo:           02-EVO-X3
Pesi:           yamz-labs/MiMo-V2.6-Flash-MOPD-EXL3-Yamz
Revision:       f895a38f1a3401cf61c8e6f8a9d1decca5198bde
Dimensione:     105777615424 byte / 37 file
Model verify:   PASS
Kyojin commit:  a3ac00d4a32148229e66c0916fcc3282bf47a3d9
Runtime:        Python 3.12.15 / Torch 2.12.0a0+rocm7.13 / gfx1151
Extension SHA:  d724fa6fe09f100d24b04148975e521babb72ab0eb88a4322acd18e21209f2f4
Patch SHA:      e63b01302fd5cb9d5c9a1fa46387959166d06b6b0eba382f6c673d1230684606
```

Il pacchetto verificato comprende 14 shard, `zz-e2e-step120.safetensors`, l'intera directory `drafter/`, tokenizer, template, config, indice, metadati e licenze. Nessun checkpoint Xiaomi originale o GGUF storico è stato scaricato in questa destinazione.

## Profilo residente

```text
Service:       mimo-kyojin.service
API:           127.0.0.1:18571/v1
Context:       40960
DFlash:        attivo
ndt:           7
Lossless:      attivo
SpecGate:      disattivato
Sessioni:      1
Boot enable:   no
```

Health finale: `{"ctx": 40960, "dflash_loaded": true, "generator": true, "lossless": true, "model": "mimo-mopd-kyojin", "ndt": 7, "spec_gate": null, "status": "ok"}`.

## Collaudo BASE

- risposta nonstreaming: PASS (`BASE_READY`);
- SSE: PASS;
- thinking nativo: osservato, 42 caratteri reasoning nel controllo dedicato;
- livello HIGH separato: non disponibile; `reasoning_effort` non è inoltrato dal server;
- DFlash: caricato e realmente esercitato;
- richiesta dedicata DFlash: 31 draft accettati, 3 rifiutati;
- cancellazione posseduta: PASS, delta osservato, drain confermato;
- richiesta successiva: PASS, `RECOVERY_READY` esatto;
- forward NODE01→NODE02: PASS, `FORWARD_READY` esatto;
- client repository MiMo: PASS, `CLIENT_READY` esatto.

Il primo tentativo di cancellazione è conservato come errore tecnico del wrapper: dopo aver impostato il cancel, il logging chiamava `sys.stderr` senza importare `sys`. È stato corretto con un delta HTTP/observability che non tocca modello, sampler o matematica; il test ripetuto ha superato cancellation e drain.

## Misure limitate

| Input sintetico | Prefill mediano | Decode mediano | Limite |
|---|---:|---:|---|
| ~8K | 688.914 tok/s | 20.279 tok/s | continuazioni naturali 9–11 token |
| ~32K | 611.238 tok/s | 14.397 tok/s | continuazioni naturali 1/9/9 token |

`cache_n=0` in tutte le sei repliche. I valori di prefill sono utili come osservazione locale; i decode non sono confrontabili con benchmark pubblici a 128 token perché le risposte si sono fermate naturalmente molto prima.

Il confronto plain/DFlash bit-identico non è stato eseguito: i quattro avvii autorizzati sono stati consumati da due avvii BASE, dal tentativo LONG e dal ripristino BASE. Non si inferisce la parità esatta dalla sola modalità lossless.

## LONG

Il tentativo `196608` ha usato il terzo avvio autorizzato. Il memory guard ha terminato il processo posseduto prima di READY per proteggere la riserva obbligatoria di 8 GiB:

```text
InvocationID:  5308b6d7f75a4f37b05696398953b3fb
READY:         no
Richieste:     0
Durata:        46,608 s
Peak memory:   52,8 GiB cgroup
Peak swap:     2,5 GiB cgroup
Esito:         BLOCKED_MEMORY_GUARD
```

Il quarto e ultimo avvio ha ripristinato BASE 40960. Di conseguenza i lavori codice 64K e documentale 128K sono `NOT_RUN`; l'installazione non è 128K qualificata.

## Budget

```text
Avvii:                 4/4
Richieste:              17/18
Output addebitato:      2847/120000 token
Ledger finale:          COMPLETE
```

## Accesso

Il forward NODE01 è `mimo-kyojin-forward-node02.service`, manuale/statico. È stato verificato con una richiesta completa e con il client del repository MiMo. Per il PC usare la procedura in `README_USO.md`; il listener SSH NODE01 sulla porta 7777 e l'indirizzo Wi-Fi `192.168.1.12` sono stati riconciliati, ma questa sessione non controlla il computer Windows dell'utente.

## Preservazione NODE01

Durante l'intero incarico:

```text
Qwen/Gufo requests: 0
qwen-gufo InvocationID: db5abd0b75c9404e8e09b217e93c9c51
HaloClu InvocationID:   32b7c76849a54704bb56fce19f908451
Riavvii Qwen/Gufo: 0
DS41: OFF
```

## Stato finale

- NODE02: MiMo BASE READY;
- NODE01: forward privato attivo;
- Gufo/HaloClu: invariati e utilizzabili;
- LONG: non ammesso per memoria;
- nessun push, reboot, aggiornamento globale o modifica dell'avvio al boot.
