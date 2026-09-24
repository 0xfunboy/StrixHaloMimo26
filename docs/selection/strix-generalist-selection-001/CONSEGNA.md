# STRIX-GENERALIST-SELECTION-001 — consegna verificata

**24 settembre 2026. Workflow terminale con blocker; confronto a quattro profili parziale.** Nessuna promozione generalista, nessun port HaloPipe o nuovo esperimento automatico.

## Risultato principale

| Profilo | Nodi | Pannello nuovo | Esito | Tempo totale delle 12 richieste |
|---|---:|---|---|---:|
| Qwen AgenticRequant Vulkan, xhigh | 1 | 12/12 tentativi | **3 PASS, 8 incompleti, 1 errore di formato** | 1883,16 s |
| MiMo mixed HIP, thinking ON | 1 | Non ammesso | Sanity clamp senza return; 12 casi NOT_RUN | Non misurato |
| DeepSeek V4.1 Flash Q2 E1, effort100 | 2 | 12/12 tentativi | **3 PASS, 9 incompleti** | 4054,68 s |
| MiMo originale TP2, thinking ON | 2 | Non ammesso | Sanity JSON con fence Markdown; 12 casi NOT_RUN | Non misurato |

Q ha completato il pannello in 31 minuti e 23 secondi di tempo cumulativo HTTP; D in 67 minuti e 35 secondi. Sono inclusi errori e incompleti, esclusi load, sanity e restore. Q e piu rapido nelle dodici osservazioni appaiate, ma i tre successi non sono esattamente gli stessi: non viene dichiarata equivalenza o superiorita statistica.

## Tutti i dodici casi

| Caso | Famiglia | Qwen Q | DS4.1 D |
|---|---|---|---|
| CODE-IT | CODE | INCOMPLETE_OUTPUT_CAP | INCOMPLETE_OUTPUT_CAP |
| CODE-EN | CODE | INCOMPLETE_OUTPUT_CAP | INCOMPLETE_OUTPUT_CAP |
| DATA-IT | DATA | PASS | PASS |
| DATA-EN | DATA | INCOMPLETE_OUTPUT_CAP | INCOMPLETE_OUTPUT_CAP |
| MATH-IT | MATH | INCOMPLETE_OUTPUT_CAP | INCOMPLETE_OUTPUT_CAP |
| MATH-EN | MATH | INCOMPLETE_OUTPUT_CAP | INCOMPLETE_OUTPUT_CAP |
| DOCS-IT | DOCS | INCOMPLETE_OUTPUT_CAP | INCOMPLETE_OUTPUT_CAP |
| DOCS-EN | DOCS | INCOMPLETE_OUTPUT_CAP | INCOMPLETE_OUTPUT_CAP |
| SCI-IT | SCIENCE | PASS | PASS |
| SCI-EN | SCIENCE | INCOMPLETE_OUTPUT_CAP | INCOMPLETE_OUTPUT_CAP |
| OPS-IT | OPS | FAIL_FORMAT | PASS |
| OPS-EN | OPS | PASS | INCOMPLETE_OUTPUT_CAP |

M e O: tutti i dodici casi NOT_RUN, non dodici risposte sbagliate. I riferimenti corretti e i validator sono indipendenti dagli output di qualunque modello.

## Decisione per famiglia

**Codice, ottimizzazione vincolata e fonti primarie:** nessuna risposta finale Q/D entro il budget; nessuna configurazione qualificata per questi compiti.

**Contratti dati e ragionamento tecnico-scientifico:** un PASS su due per entrambi, nei casi italiani DATA-IT e SCI-IT. Evidenza positiva circoscritta, non qualifica della famiglia.

**Decisioni operative simulate:** un PASS su due per entrambi, su casi diversi. Q passa OPS-EN; D passa OPS-IT. Nessuna azione proposta dal modello e stata eseguita sul cluster.

## Errori e limiti concreti

Gli otto incompleti Q e i nove incompleti D non hanno consegnato alcun carattere di finale. Sono ragionamenti non chiusi al cap, non programmi finali che hanno fallito i test. Cap fissi4096/8192, context16384; input reali del pannello Q/D non oltre1606 token. Nessuna estensione o chiusura forzata del thinking.

Q: 56841 token totali, 55807 di reasoning, 1026 finali, piu8 token di controllo. D: 60783 totali nativi; conteggi reasoning/finale separati non disponibili. Nessuna ritokenizzazione spacciata per conteggio nativo.

OPS-IT di Q ha un oggetto corretto racchiuso in ```json: FAIL_FORMAT perche il contratto richiede JSON puro. Il corpo coincide con la risposta D verificata rispetto all’expected indipendente, ma nessun fence e stato rimosso per concedere un PASS.

M: cinque sanity PASS, clamp FAIL_CODE_TEST. La funzione assegna il valore a una variabile senza return; i quattro test ottengono None. O: cinque sanity PASS, JSON FAIL_FORMAT; alpha7 e beta blue sono corretti, ma la risposta include fence Markdown. Entrambi sono stop del gate di ammissione, non una dimostrazione di corruzione del runtime.

## MTP: il blocco effettivo

Il limite HTTP era gia noto ed e stato risolto nel piano con avvii OFF/ON separati. Il collector aggiuntivo OFF ha pero cercato una proprieta /props inesistente: la modalita reale era in params["speculative.types"], valore none. L’errore e del nostro collector. Zero continuazioni reference OFF inviate; il Q principale ha comunque completato32 record e il suo restore. Non si inventano le reference e non si aggiungono caricamenti fuori budget. MTP ON non eseguito, nessun TPS MTP o verdetto di equivalenza.

## Misure motore nuove, separate dal reasoning

Thinking OFF, greedy, speculazione OFF. Ogni riga contiene tre misure valide con128 token effettivi; warmup esclusi, cache riusata0. Valori: mediana [minimo–massimo].

| Profilo / input reali | Prompt engine tok/s | Decode nativo tok/s | HTTP completo, secondi |
|---|---:|---:|---:|
| Q / 2111 token | 478,30 [475,48–479,21] | 29,01 [28,40–29,08] | 8,90 [8,79–8,91] |
| Q / 8329 token | 485,75 [484,27–485,91] | 27,86 [27,76–28,22] | 21,72 [21,65–21,76] |
| D / 2045 token | 93,44 [93,23–93,56] | 16,85 [16,81–16,86] | 29,55 [29,50–29,58] |
| D / 8154 token | 147,14 [147,10–147,19] | 16,67 [16,66–16,70] | 63,15 [63,13–63,15] |

**Contratti differenti:** Q prompt-time include il primo campionamento e il decode e post-first-token. D espone rate totali arrotondati nei log e include il primo token nel decode. Non viene calcolato uno speedup Q/D da queste colonne. TTFT client e primo token finale non osservabili con questi collector restano null. Nessun nuovo benchmark M/O: i numeri MiMo storici non riempiono queste celle.

## Load e costo dei blocchi

| Profilo | Load principale, secondi | Sanity preflight |
|---|---:|---|
| Q | 95,57 | 6/6 PASS |
| M | 114,18 | 5/6 PASS, gate fallito |
| D | 132,34 | 6/6 PASS |
| O | 280,51 | 5/6 PASS, gate fallito |

D-001 e conservato separatamente: E1 era caricato ma il collector attendeva /health inesistente. Zero richieste. La singola correzione di packaging ammessa ha usato /v1/models con identita e context verificati, nuove unit e freeze prima di D-002. Il tentativo setup, inclusa la sua restituzione al residente, dura1137,26 secondi; non e un retry semantico.

La memoria rimane descritta con snapshot MemAvailable/VmSwap/I/O e osservatore per nodo nei raw. Non sommiamo RSS, UMA e GPU come consumi distinti; non sono picchi continui o una prova di assenza di throttling.

## Restore e integrita

| Run | Esito | Restore K2, Europe/Rome |
|---|---|---|
| generalist-selection-001-Q-001 | PASS | 2026-09-24T10:53:53+0200 |
| generalist-selection-001-M-001 | FAILED | 2026-09-24T11:01:01+0200 |
| generalist-selection-001-D-002 | PASS | 2026-09-24T12:43:29+0200 |
| generalist-selection-001-O-001 | FAILED | 2026-09-24T16:23:52+0200 |
| generalist-selection-001-D-001 | INTERRUPTED | 2026-09-24T11:19:59+0200 |

Verifica live finale: **2026-09-24T16:29:07+0200**, K2 READY, owner DS41/RUNNING, epoch `1790259544584609152`, release `5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513`; rank0/rank1/paired HTTP200. Processi delle campagne assenti, lock rilasciati; gli EngineCore DS41 residenti sono stati preservati.

569 artefatti dei run archiviati byte-identici (538 NODE01, 31 NODE02). Prefissi registrati verificati: Q32, D32, M6, O6; O ha le stesse sei risposte su entrambi i rank, non repliche ulteriori. Nessuna richiesta pendente.

Freeze originali invariati:74 file, addendum continuita15, recupero readiness D13. Preservati741 file delle campagne precedenti e44 scratch. Ricalcolo CPU **CONTINUITY_EVALUATION_CHECK_PASS**, stesso report, JSON e coppie; nessuna inferenza durante la consegna.

Preparazione: `87442a8e1b999e5f33165d0b6b563eac5248ab15`. Addendum: `efae11dae82e322f581db0de1d3ad0226e5ce37d`. Recupero D: `dba8594d2b20d7177b74fe3c8c4c5055a7996243`. L’indice originale effettivo e `06c85aae8b6a323a09067725cbf7656fd9cd19df56918c50d95881e0d3284604`: il diverso SHA comunicato in precedenza era un errore di trascrizione, non una modifica del freeze. Il commit finale e riportato nella ricevuta di consegna e nella cronologia Git di questo file.

## Riuso e decisione finale

Le quattro campagne Qwen storiche sono documentate e i report essenziali sono gia stati recuperati dall’archivio verificato, senza ricaricare i vecchi modelli. QWEN_HISTORY_AND_REUSE.md distingue IQ4_XS, Q5/RPC, IQ3 target e IQ3 MTP+ngram dal nuovo AgenticRequant/Vulkan. Lo storico ha guidato i controlli, non sostituito le nuove risposte.

**Nessun vincitore generalista qualificato.** Q e piu rapido nel pannello raccolto e usa un nodo, ma3/12 non basta; D ottiene gli stessi tre PASS complessivi, non gli stessi tre casi. MiMo non e valutabile sul pannello. Non avvio HaloPipe per accelerare una configurazione che non consegna ancora i task nel budget. La matrice statica di cooperazione sulla stessa richiesta e in COOPERATION.md.

**Unica prossima azione proposta, non eseguita:** qualificare un profilo Qwen con sforzo nativo low, conservando target, runtime, temperatura, cap e contesto. Serve nuova autorizzazione/preregistrazione; nessun nuovo test e partito.

## Percorsi e verifica

Root canonica:
```text
/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001
```

File: REPORT.md, summary.json, paired-results.jsonl, raw-results.jsonl, REVIEW_NOTES.md, QWEN_HISTORY_AND_REUSE.md, COOPERATION.md, NEXT_EXACT_ACTION.md, verification.json, evidence/, sources/ e gli indici degli addenda.

Comando effettivamente verificato, CPU-only:
```bash
cd /home/funboy/StrixHaloMimo26
PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 python3 docs/selection/strix-generalist-selection-001/continuity/evaluate_continuity.py --root docs/selection/strix-generalist-selection-001 --check
```

Richiede i raw originali e il sandbox Podman locale fissato. Il pacchetto di lettura non e un runtime portabile e non contiene pesi o tutti i raw. Nessun push o deployment.
