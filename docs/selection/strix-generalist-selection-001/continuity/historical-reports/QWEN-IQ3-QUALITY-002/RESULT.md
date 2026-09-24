# QWEN-IQ3-QUALITY-002 — risultato funzionale finale

## Verdetto

Su questo corpus locale, **A e B risolvono entrambi gli 8 problemi di ragionamento; nessuno dei due completa i 12 compiti di programmazione entro il budget congelato di 3.072 token**. Tutte le 40 richieste sono state eseguite una volta, senza retry, riparazione, aumento del budget o modifica dei prompt.

B riduce il tempo HTTP complessivo degli 8 problemi risolti da **375,256 a 304,471 s: −18,86%, rapporto A/B 1,2325×**. Includendo anche i 12 tentativi incompleti, il risparmio sull'intera suite è **−5,03%**, non 3×. Non è una misura a parità di sequenza generata: B produce un numero di token diverso nei problemi naturali.

Non osserviamo risposte finali errate nei problemi completati; questo non dimostra equivalenza generale di intelligenza. Per i nuovi programmi il verdetto è **INCOMPLETE**, non corretto e non errore funzionale dimostrato. La fedeltà esatta A/B rimane **FAIL in 20/20 casi** e viene riportata separatamente dal successo funzionale.

## Protocollo e identità

- Modello: Qwen3.8-Flash-Next Unsloth **UD-IQ3_XXS**, stessi tre shard e stessa chiusura binaria EngramHalo in A/B. I pin completi sono in `a/identity.json`, `b/identity.json` e `audit-results.json`; nessun nuovo hash integrale dei pesi durante questo audit.
- A: target-only. B: `draft-mtp,ngram-mod`, `n_max=4`, `p_min=0.75`, sidecar EasiiX Q8_0. Il confronto non isola il contributo del solo MTP da quello della cache n-gram.
- Un solo nodo/GPU `ROCm0` per ciascun braccio, eseguiti in successione: **nessun TP2 o calcolo distribuito misurato qui**. `parallel=1`, contesto 8.192, KV F16/F16, batch 8.192, ubatch 2.048, 4 thread, Flash Attention on, caricamento `SSD/mmap/lazy`, reasoning preservato.
- Tutti i 20 prompt: `temperature=0`, `seed=1`, `reasoning_effort=xhigh`, `enable_thinking=true`, massimo 3.072 token, chat non streaming. Una prima risposta per compito, nessuna ripetizione e nessun warmup del corpus.
- Manifest congelato prima delle risposte: SHA-256 `bee9f07b13a17f90c144dfaf6bfc5e4a08ae983cc0ecb7faf1d8cea59a81d9a7`. Domande, ordine, oracoli e sorgenti identici in A/B.
- Il documento lungo ha **3.106 token di input renderizzato** in entrambi i bracci; input più budget occupano 6.178/8.192 token, con margine 2.014. Nessuna truncation del contesto registrata.
- A: 2026-09-06 14:48:23–15:21:49 UTC. B: 16:06:53–16:38:38 UTC. Un solo A seguito da un solo B, senza azzerare la cache del sistema operativo: non sono campioni contemporanei o alternati; cache/memoria e storia delle richieste possono influire.

## Esiti e costo effettivo

| Metrica | A target-only | B MTP + n-gram |
| --- | ---: | ---: |
| Richieste HTTP valide / pianificate | 20/20 | 20/20 |
| Ragionamento: corretto, fine naturale | 8/8 | 8/8 |
| Programmazione: corretto | 0/12 | 0/12 |
| Programmazione: INCOMPLETE al cap | 12/12 | 12/12 |
| Wrong answer / code fail / timeout HTTP | 0 / 0 / 0 | 0 / 0 / 0 |
| HTTP totale, tutti i tentativi | 2.006,046 s | 1.905,229 s |
| HTTP dei soli problemi corretti | 375,256 s | 304,471 s |
| HTTP dei 12 tentativi di codice incompleti | 1.630,790 s | 1.600,757 s |
| Secondi per soluzione corretta, **includendo tutti i tentativi** | 250,756 | 238,154 |
| Secondi per soluzione corretta, escludendo i tentativi incompleti | 46,907 | 38,059 |
| Token generati totali, inclusi ragionamento e finali | 45.121 | 45.146 |
| Token generati negli 8 problemi risolti | 8.257 | 8.282 |

Il costo per soluzione corretta del solo codice è **non definibile**, perché le soluzioni complete sono zero. Non si scartano i suoi tempi dal costo complessivo. `COMPLETE` nei due `summary.json` significa che il protocollo ha tentato tutte le richieste, non che tutti i compiti siano riusciti.

Nei 24 tentativi di codice il contenuto finale è la stringa vuota, `finish_reason=length`, stop nativo `limit`, 3.072 token. È presente testo nel campo di ragionamento, ma non una risposta finale utilizzabile. Il classificatore congelato non esegue il sandbox su una risposta al cap: **nessun nuovo programma è stato qualificato**. Non si può stabilire da questa prova se con altro budget i programmi sarebbero terminati correttamente.

## Tutti i 20 compiti

Ordine effettivo del manifest. `I` = INCOMPLETE in entrambi i bracci; `P` = PASS naturale in entrambi. Token e secondi HTTP sono riportati come A / B. L'ultima colonna è il primo indice di token differente, a base zero, includendo il ragionamento.

| Compito | Tipo | Esito A/B | Token A / B | HTTP s A / B | Prima differenza token |
| --- | --- | --- | ---: | ---: | ---: |
| `ttl_lru_state` | codice | I / I | 3072 / 3072 | 137,043 / 132,985 | 49 |
| `slot_constraint_schedule` | ragionamento | P / P | 552 / 506 | 24,388 / 18,215 | 162 |
| `subtract_half_open` | codice | I / I | 3072 / 3072 | 135,745 / 131,963 | 4 |
| `conditional_urn_fraction` | ragionamento | P / P | 461 / 463 | 20,634 / 16,687 | 100 |
| `negative_path_cost` | codice | I / I | 3072 / 3072 | 135,843 / 129,905 | 95 |
| `settlement_largest_remainder` | ragionamento | P / P | 1804 / 1729 | 79,231 / 58,095 | 5 |
| `escaped_pairs_parser` | codice | I / I | 3072 / 3072 | 135,811 / 128,785 | 44 |
| `portfolio_dependency_optimum` | ragionamento | P / P | 1673 / 1883 | 73,259 / 72,640 | 66 |
| `stable_room_assignment` | codice | I / I | 3072 / 3072 | 135,782 / 130,785 | 124 |
| `nested_transaction_state` | ragionamento | P / P | 1045 / 1051 | 46,171 / 33,588 | 11 |
| `fragmented_utf8` | codice | I / I | 3072 / 3072 | 135,654 / 137,006 | 164 |
| `minimal_fault_diagnoses` | ragionamento | P / P | 634 / 681 | 28,215 / 24,634 | 28 |
| `strict_netstrings` | codice | I / I | 3072 / 3072 | 135,393 / 138,381 | 4 |
| `grounded_revision_selection` | ragionamento | P / P | 854 / 679 | 49,446 / 34,201 | 10 |
| `exact_cent_apportionment` | codice | I / I | 3072 / 3072 | 135,901 / 130,078 | 73 |
| `single_bad_modular_sensor` | ragionamento | P / P | 1234 / 1290 | 53,912 / 46,412 | 380 |
| `simultaneous_text_edits` | codice | I / I | 3072 / 3072 | 136,004 / 131,594 | 245 |
| `event_window_counts` | codice | I / I | 3072 / 3072 | 135,817 / 136,815 | 197 |
| `integer_expression_parser` | codice | I / I | 3072 / 3072 | 135,977 / 131,803 | 39 |
| `alias_chain_resolution` | codice | I / I | 3072 / 3072 | 135,821 / 140,658 | 132 |

Tutti gli otto JSON finali sono semanticamente corretti, con i tipi numerici richiesti, senza chiavi extra e senza Markdown. Sette coppie di finali sono anche identiche come testo; `grounded_revision_selection` cambia solo indentazione/spazi del JSON finale. Ciò **non** significa che i ragionamenti siano identici: le sequenze complete differiscono in tutti i compiti. Le dodici coppie di contenuti finali vuoti non contano come risposte corrette o fedeltà utile. Non ci sono repeat per stimare la ripetibilità della nuova suite.

## Decode, acceptance e cosa non è misurato

| Aggregato | Mediana decode A | Mediana decode B | Intervallo B | Acceptance B, token accettati/proposti |
| --- | ---: | ---: | ---: | ---: |
| Tutti i 20 compiti | 22,7951 tok/s | 23,8731 tok/s | 22,0074–32,6997 | 21.266 / 27.038 = 78,6523% |
| 8 problemi risolti | 23,3424 tok/s | 29,1965 tok/s | 26,3891–32,6997 | 5.048 / 6.256 = 80,6905% |
| 12 tentativi di codice incompleti | 22,7831 tok/s | 23,4592 tok/s | 22,0074–24,0270 | 16.218 / 20.782 = 78,0387% |

Sono mediane **tra compiti diversi**, non tre o cinque repliche dello stesso benchmark. Decode è il contatore nativo verificato `(token_generati−1)/predicted_ms`; HTTP comprende l'intera richiesta. Acceptance è il rapporto dei contatori sommati, non la media delle percentuali e non una verifica della correttezza. A non genera proposte speculative.

B ha HTTP inferiore in 16/20 compiti, inclusi tutti gli otto risolti. Il −18,86% HTTP è un vantaggio osservato in questa sequenza, **non un miglioramento qualificato ripetibile o attribuibile al solo MTP**. I numeri storici fino a circa 93 tok/s su altro prompt/modalità non sono riprodotti da questo xhigh.

**TTFT client non misurato**: le richieste non sono streaming, e `prompt_ms` non è TTFT. Non è esposto un conteggio `usage.completion_tokens_details.reasoning_tokens` in nessuna delle 40 risposte: il numero separato di token di ragionamento è **N/D**, non zero. I conteggi totali sono reali e verificati con gli ID; la lunghezza in caratteri del campo reasoning non viene convertita in token. Non attribuiamo percentuali a draft, verifica, sincronizzazione, prefetch o paging senza timer causali.

## Memoria e major fault: intervalli effettivi

Sono 22 snapshot per braccio: prima, dopo ciascun compito, dopo l'ultimo. Stesso PID/start time dentro ogni intervallo; i due bracci hanno processi distinti. Queste sono misure del **nodo locale**, non un totale dei due EVO-X3.

| Misura | A | B |
| --- | ---: | ---: |
| PID | 1558208 | 1579376 |
| Durata intervallo telemetria | 2.006,308 s | 1.905,548 s |
| Major fault del processo, delta | **+1.026** | **+70** |
| RSS prima → dopo | 0,887 → 10,909 GiB | 1,717 → 12,036 GiB |
| RSS massimo campionato | 10,909 GiB | 12,107 GiB |
| GTT GPU massimo campionato | 50,840 GiB | 54,948 GiB |
| MemAvailable minimo campionato | 58,608 GiB | 53,738 GiB |
| VmSwap del processo, massimo campionato | 0 | 0 |
| Swap usato dal sistema, massimo campionato | 4,128 GiB | 4,113 GiB |

**Non è una prova zero-major-fault.** A registra +461 major fault nel primo intervallo e +150 nell'intervallo del documento lungo; B rispettivamente +6 e +1. Con mmap/lazy e sequenza A→B, lo stato delle pagine/cache non è equivalente: non attribuiamo l'intera riduzione del tempo alla sola speculazione. VmSwap nullo del processo non significa swap di sistema nullo. Gli snapshot non misurano il picco continuo né la durata delle attese per paging. **RSS, GTT e VRAM non si sommano su UMA.**

## Evidenza separata: stress dei vecchi programmi thinking-OFF

[HISTORICAL-CODE-STRESS.md](HISTORICAL-CODE-STRESS.md) documenta un controllo retrospettivo distinto: **A 8/8, B 8/8 PASS** sui 16 programmi già salvati in SPEED001, con nuovi casi limite/proprietà deterministiche. Sono otto tipi di problema, non sedici problemi indipendenti; quattro coppie hanno codice identico.

I nuovi test erano congelati prima di leggere quei programmi; il controllo degli oracoli aveva dato **8 reference PASS / 8 mutant FAIL**. L'esecuzione è avvenuta nel sandbox esistente senza nuove generazioni. Il presente audit non li ha eseguiti nuovamente. Questa evidenza sostiene l'utilità di quegli output thinking-OFF sui casi controllati, **non** completa i dodici nuovi compiti xhigh, non modifica il punteggio e non produce nuovi TPS del modello.

Non è stato eseguito GLM sul nuovo corpus: il vecchio screening GLM su quattro risposte e la conferma di un solo prompt non costituiscono un benchmark comparabile a questi venti problemi. Nessuna graduatoria generale di intelligenza, equivalenza alla quantizzazione superiore, SWE-bench o garanzia di correttezza produttiva può essere derivata qui.

## Verifica e percorsi raw

Radice canonica: `/home/funboy/ai-exp/reports/moe-cluster/QWEN-IQ3-QUALITY-002/`.

- `manifest.json`, `manifest-sha256.json`: corpus, richieste, oracoli e sorgenti congelati.
- `a/` e `b/`: `identity.json`, `runtime-maps.json`, `protocol.json`, `sandbox-preflight.json`, `summary.json`; per ogni ID della tabella: `<id>-intent.json`, `<id>-raw.json`, `<id>-result.json`, `<id>-telemetry.json`; `telemetry-before.json` e `telemetry-after.json`.
- `audit_results.py` e `audit-results.json`: audit offline eseguito **una sola volta**, senza HTTP, azioni sui servizi o esecuzione dei programmi generati. Verifica byte base64/JSON/request, stato HTTP, schema, ID/count/stop/timing, pin del manifest/sorgenti e identità A/B; ricalcola gli otto giudizi JSON, metriche, aggregati, confronti token e telemetria. Receipt dei preflight sandbox coerenti; nessuna receipt di nuovo codice richiesta perché tutti i programmi sono incompleti.
- `a-journal.log`, `b-journal.log`: journal conservati dal coordinatore; nessun nuovo profiling causale ricavato da questi log nel presente audit.
- SHA-256 `a/summary.json`: `0185d6c3883ad111cd30d25c6618892dc3cfb2bb499e3cd7b9787cf625780e16`.
- SHA-256 `b/summary.json`: `3835022fc23fa9a2e3964fb057b98f6ed2beade8ecdd6d4b5cb5c577183182b5`.
- SHA-256 `audit-results.json`: `04e6b6e1788110bc8f4cefab33037aaeba5369f242478e484ebab41e106ae539`; contiene anche gli hash dei singoli JSON raw.
- Evidenza retrospettiva: `historical_code_stress.py`, `historical-code-stress-freeze.json`, `historical-code-stress-results/pre-read.json`, `historical-code-stress-results/{a,b}-<id>.json`, `historical-code-stress-results/summary.json`, `HISTORICAL-CODE-STRESS.md`. I vecchi raw restano in `/home/funboy/ai-exp/reports/moe-cluster/QWEN-IQ3-SPEED-001/{a,b}-utility/`.

## Stato operativo

**GLM ripristinato e mantenuto attivo; campagna conclusa, nessun test pendente.** Il controller ha ripristinato il profilo originale GLM CIRU TP2 con DFlash `k=5`, `local_draft=0`, preset normale di ragionamento `max`, `safe_prefill=true`, `canonical_moe=true`, entrambi i flag di trace falsi. Owner `promoted`, epoch `1788712765221`.

La receipt `restored_retained` è in `/home/funboy/ai-exp/reports/moe-cluster/CIRU-TP2-001/iq3-quality-restore-k5-001/restoration-1788712946485074721.json`. Nello stesso run, `api-restoration/summary.json` registra **3/3 PASS**: completion streaming, chat JSON e chat streaming. È un controllo API breve con reasoning `low`, non una nuova prova di qualità/prestazioni e non una modifica del preset normale `max`.

Le evidenze finali della presente radice confermano:

- `final-health.json`: entrambi i rank pronti, `busy=false`, `poison=null`.
- `final-pair-status.json`: coppia originale ripristinata, stato `promoted`.
- `final-local-units.txt` e `final-remote-units.txt`: due rank più frontend attivi, tutti con `RuntimeMaxUSec=infinity`; servizio IQ3 inattivo. Il controller ha verificato PID/Invocation delle precedenti unità sulle porte 8080/50052 invariati.

Nessun nuovo benchmark GLM è stato eseguito: la qualifica precedente è preservata tramite il ripristino verificato, non sostituita da TPS inventati. Questo audit ha soltanto letto tali receipt; non ha eseguito richieste modello, sandbox o azioni sui servizi.
