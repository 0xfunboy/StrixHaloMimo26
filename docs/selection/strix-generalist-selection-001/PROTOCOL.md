# STRIX-GENERALIST-SELECTION-001 — protocollo preregistrato

## Autorità e stato

Mandato dell’utente: STRIX_GENERALIST_SELECTION_001_MANDATO_2026-09-24(1).md, letto integralmente dall’allegato della conversazione; SHA256 4c0740dab543f2bb6f63f1a47319323a84eb8f1c705026333897bc4a7d6025ab, 26656 byte. Il documento originale è un allegato, non una misura. Il presente file definisce l’esecuzione concreta e i limiti verificati, senza modificare gli obiettivi del mandato.

Base locale e6a814336e6f37e88b1cd3a5fab23fc5b299635d, branch perf/mimo26-strix, repository /home/funboy/StrixHaloMimo26. Campagna nuova e separata: PERF-BASELINE-001, QUALITY-RETENTION-001, QUALITY-HOLDOUT-002 e i lotti DS4/HaloPipe terminali non sono riaperti o riscritti. Le loro evidenze e i 44 file scratch all’ingresso sono inventariati in preflight/entry.json.

NODE01 è 01-EVO-X3, funboy, tramite StrixMCP — EVO 01. NODE02 è 02-EVO-X3, raggiunto da NODE01 con SSH 02-evo-x3-tb, IdentityAgent=none, BatchMode=yes. La prima riconciliazione ha trovato K2 dspark-k2-gfx1151, release5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513, owner DS41/RUNNING e READY; il controller effettivo e le InvocationID sono registrati. Quello snapshot non autorizza a imporre un epoch storico: admission.json deve verificare nuovamente owner, unità, salute e assenza di richieste/lock prima della sospensione.

## Domanda e confini

Confrontare quattro profili completi per correttezza di compiti nuovi, durata delle richieste e uso delle risorse. Il criterio primario è correttezza, non TPS. Non si misura la percentuale di intelligenza conservata, l’effetto causale del thinking rispetto ai lotti vecchi, né la varianza stocastica. Un solo campione per caso/profilo non prova superiorità statistica.

Nessun aggiornamento globale, tuning, nuovo backend alternativo, NVIDIA, RDMA, modifica dei servizi/release DS41, power policy, TTM, clock, BIOS, rete, swapoff o cache flush. Nessun modello aggiuntivo oltre al target/sidecar Qwen autorizzato. Nessuna pubblicazione, push, PR, promozione o port HaloPipe.

## Asset e runtime Qwen

Fork drluoto/llama.cpp congelato al commit ba5354d46ca63e8225c28e1331f0f7651723ad05; checkout separato /home/funboy/ai-exp/strix-generalist-selection-001/qwen-runtime e build separata qwen-build. Ricetta drluoto/flash-next-strix-halo al commit b70c03f15e41ec2635c75c8bfa2dfeb2026c7fcd. Vulkan/RADV con il sistema esistente; niente modifiche ai driver.

Un solo intervento di compatibilità per la dipendenza header SPIRV-Headers mancante: tag vulkan-sdk-1.4.341.0, commit04f10f650d514df88b76d25e83db360142c7b174, installato nel solo prefix della campagna. Sono conservati il primo fallimento CMake, il fallimento di propagazione include e la build riuscita con include path isolato. Nessun sorgente numerico Qwen è stato modificato. Non è stato eseguito un secondo tuning numerico.

Target drluoto/Qwen3.8-Flash-Next-AgenticRequant-Q5K-GGUF revision d69cf601fafd166c9d39caa0ab41fd1ab51a0763: soltanto trunk-q5k-00001-of-00003.gguf, 00002 e 00003. Il trunk Q5_K non rende tutti gli esperti Q5: i descriptor GGUF reali sono nel relativo inventario. Sidecar esatto mtp-Qwen3.8-Flash-Next-Q5_K-frspec-65k.gguf, repository MTP revision ac875a98457a8effe8fb83de8f3701421f507a24. Tokenizer/template ufficiale Qwen revision de4b8e4d43b917e7706784d8bb445c9af86a3540.

I quattro file pesi totalizzano95029753856 byte, meno di110GiB. Manifest e revisioni sono anteriori al trasferimento. Resume HTTP Range limitato e hash esatti, senza download di varianti ulteriori o DS4/MiMo. Riserva minima60GiB dopo i pesi e allowance12GiB per workspace/log. I file già corretti non sono riscaricati. Acquisizione/hash/build devono essere terminali prima delle finestre modello e delle misure.

## Quattro profili

Tutti: context16384, una sequenza, text-only, speculazione OFF, stato di richiesta nuovo, EOS naturale, una sola generazione. Le configurazioni complete sono config-Q/M/D/O.json e source-manifest.json. Ambiente dei worker esplicito e isolato con env -i; HOME e bus utente sono quelli esistenti, non vengono cambiati globalmente.

Q: target Qwen sopra, NODE01 Vulkan0, all GPU layers, splitnone, batch2048/ubatch2048, slot1, no continuous batching, FAon, KVf16/f16, load-mode dio. Qualità con thinking ON e template ufficiale xhigh. temperature1, top_p.95, top_k20, min_p0, repeat_penalty1, presence/frequency0, seed101. Nessun limite artificiale del reasoning o chiusura iniettata.

M: Baekpica MiMo-V2.6-Flash-RL MQ-IQ2-XXS-XS-Q8-MM-BF16 revision b3794b22b6276f8120c340f52639f5eaa354a3fd, quattro shard main esistenti. llama.cpp HIP58367713a6935c0810103378144008df32e3d5db, NODE01 ROCm0, splitnone, all layers, batch512/ubatch128, slot1, no continuous batching, FAauto, KVf16/f16. enable_thinking=True nel renderer reale. temperature1, top_p.95, top_k0(disabilitato), min_p0, penalty1/0/0, seed101. mmproj/MTP/DFlash OFF. Il template ON non preinserisce <think>, a differenza di Q; il collector rileva i token realmente emessi e non inventa reasoning quando il modello risponde direttamente.

D: DeepSeek-V4.1-Flash-Q2.gguf esistente, due nodi con release nativa E1 ds4-speed-001-engram1, Engram concorrente. Binari immutati e uguali sui nodi; sorgente qualificato a8f44737ecc6bbd406d796d1e402b312f00d1564 archiviato separatamente. Non si usa il K2 residente come candidato E1. TCP TP2, batched-session1, contesto16384; DSpark e diagnostiche sperimentali OFF. L’API accetta reasoning_effort=max, non la stringa100: il modello V4.1 mappa max al testo nativo Reasoning Effort:100 anche a16K. Sorgente e tokenizer CPU del binario effettivo lo verificano; l’help generico su questo punto era obsoleto. Temperature1/top_p.95/top_k0/min_p0/seed101 espliciti prevalgono sui default. tools=[] e tool_choice=none impediscono i rami di riparazione/continuazione dei tool. Le risposte native espongono content/reasoning_content e conteggio totale, non gli ID generati o i conteggi separati: questi campi restano null.

O: MiMo originale Xiaomi5711b268169967567844e1e560e8a3966da959b1, esperti MXFP4 e componenti FP8, non BF16 integrale. vLLM0.1.0rc2.dev9+g9255fd9fb9.rocm100, Torch2.13.0+rocm10.0.0, Transformers5.16.1 e patchQKV eeb66fefbf1b63459e5712c031399f2d24d9ac05956c97b4e979ad03b901be72 invariati. TP2/PP1, external_launcher, text-only/eager/triton_unfused, maxseq1, maxbatched512, customallreduceOFF, EPOFF, prefixcacheOFF. KV esplicita4294967296 byte/rank, non allocazione automatica. Context16384 deve essere realmente sostenibile nell’inizializzazione. Qualità ON con stesso sampling M; top_k0 è tradotto nel sentinel -1 di vLLM, non in un filtro diverso.

Q/M/O devono conservare almeno8GiB MemAvailable dopo il caricamento, prima del pannello. Un gate di capacità o errore di runtime ferma quel profilo senza ridimensionare contesto, budget o KV. Il risultato e il restore vengono conservati; profili successivi possono proseguire soltanto con blocker esplicito isolato e restore verificato.

## Dodici fixture nuove e oracoli indipendenti

Sei famiglie, una fixture italiana e una inglese per famiglia. Non sono semplici ridenominazioni del holdout. Tutti i casi sono dichiarati sintetici; nessun dato privato di altri progetti è stato letto per costruirli.

CODE: libreria atomica di trasferimenti su due moduli e metering su finestre semiaperte con tempi interi grandi. Le risposte contengono due file completi in un JSON; vengono eseguite nel solo sandbox rootless qualificato. I test verificano comportamento, tipi, rollback e input immutabili, non uguaglianza con il codice di riferimento.

DATA: ricostruzione SLA tramite revisioni/intersezioni/differenze di intervalli; pubblicazione atomica di snapshot con checksum, migrazione schema e retry di sole parti valide. Expected letterali controllati separatamente con insiemi di minuti e simulatore di receipt.

MATH: bilancio energetico con accumulo e carico differibile; produzione robusta a due scenari con costi fissi condizionati. Ogni riferimento esatto è verificato con due formulazioni indipendenti e conteggio delle soluzioni ammissibili. Il primo problema ha150 soluzioni, il secondo4. Gli optimizer sono soltanto strumenti del valutatore, mai forniti al modello.

DOCS: certificati di calibrazione validi a istanti diversi, cutoff e autorizzazioni; cronologia transazionale con offset degli orologi, WAL e idempotenza. Sono fonti primarie, senza riepilogo che contenga le risposte. Per ogni claim sono preregistrati valori, insiemi alternativi sufficienti e riferimenti pertinenti. Un ID esistente o un totale di citazioni elevato non basta.

SCIENCE: identificazione termica, soluzione dinamica e conservazione dell’energia; probabilità con test dipendenti e politiche di ispezione distinte. Formule e ipotesi sono nel prompt, expected verificati da residui/integrazione analitica o frazioni esatte. Tolleranze dichiarate:0.01 per i numeri termici/costi/conteggi;1e-8 per le due posteriori. Non si inventa un intervallo di confidenza campionario senza dati campionari.

OPS: esito di cutover incerto con verifica obsoleta e autorizzazione scaduta; promozioni legate al digest, risultati storici e azioni solo pianificate. Le tool call sono JSON simulati e non vengono MAI invocate sul cluster.

Cap congelati: ogni caso IT8192, ogni caso EN4096, totale73728 token per profilo inclusi reasoning e finale. Sono massimi, non output forzati. Riferimenti entro i cap; input massimi misuratiQ1553, M/O1503,D1606, tutti<=3072. Input+cap+256<=16384. Fra modelli differenti si conserva il compito/testo, non si impongono ID uguali. M/O hanno input realmente identici. I renderer ON/OFF sono confrontati CPU e non applicano doppioBOS/template.

## Parser, criticità e codice

Risposta finale del pannello: un unico JSON, senza markdown/prosa. Parsing rifiuta duplicati, valori non finiti, trailing text, tipi impropri e bool al posto di numeri. Schema/forma e semantica sono distinti. Ordine delle chiavi irrilevante; ordine liste conforme alla specifica. Nessun grammar, repair, feedback o completamento aggiuntivo.

PASS richiede finale completo e tutte le condizioni. Un piano ammissibile subottimale o con totali dichiarati falsi fallisce. Gli expected dell’originale non sono ricavati dall’originale: tutti i profili usano lo stesso riferimento indipendente. Errore di fixture dimostrato dopo generazione va in case-invalid.json, simmetricamente su tutti i profili, senza modifica o replay.

Predicati critici preregistrati: rilascioB41 con prerequisiti mancanti in DOCS-IT; mutazioni non autorizzate prima della riconciliazione in OPS-IT; promozione di candidato diverso daC o dichiarazione diC già promosso senza risposta del tool in OPS-EN. Gli altri errori non sono rinominati critici a posteriori. Nessuna violazione osservata non certifica sicurezza generale.

Codice generato soltanto nell’immagine Podman esistente a58caff183f8eb10c84fce3d3eb8496e684411369848a77bfcf0af9074cc16c4, rootless, uid65534, no network/mount host/GPU, rootread-only, capdropALL, nonewprivs,256MiB,32pids,3sCPU,15swall. Import limitati ai moduli del compito, builtins controllati, attributi privati/dunder e costrutti di evasione bloccati. Setup OCI fallito è VALIDATOR_BLOCKED, non errore semantico del modello. Il codice non viene eseguito sull’host.

## Collector e metriche

Percorsi principali NONSTREAMING: Q/M native /completion con inputID congelati e outputID nativi; O LLM.generate offline; D API nativa /v1/chat/completions. Ogni richiesta salva intent esclusivo, payload, risposta nativa anche prima dei controlli, risultato atomico, digest e append index prima della successiva. Il timeout MCP non rilancia nulla.

Q/M/O separano reasoning/finale tramite token di controllo nativi e decodifica della stessa sequenza, conservando integralmente il raw. Non ritokenizzano testo per inventare ID. D conserva le sezioni native e conteggi disponibili, con trace del prompt/sampling/count per confronto con il tokenizer dello stesso binario. reasoning/final token D sono null. Un reasoning non chiuso resta senza finale; nessuna answer-room forzata.

TTFT client e primo token finale non osservabili nel nonstreaming restano null. Per O scheduled-to-first è un intervallo engine dichiarato, non prefill puro. Q/M riportano timingprompt nativi che includono il campionamento del primo token e decodepostfirst; O usa timestampenginecore per(n-1)/(last-first). D riporta i log nativi arrotondati: prefillcurrent/elapsed e decodecompletion/elapsed che INCLUDE il primo token; non viene spacciato per la stessa metrica postfirst. Tutti i contratti restano distinti.

Tempi delle richieste corrette E fallite/incomplete sono riportati, senza eliminare i fallimenti. Q/M/D misurano submitHTTP→lettura completa; O generateoffline→return. Nessun rapporto normalizzatoHTTP/offline. Una dominanza osservata si può annotare soltanto fra profili tecnicamente qualificati con12 tempi e lo stesso osservatore; non è una dominanza generale o un indice intelligenzaxTPS.

## Misure engine separate

Nello stesso caricamento: documento tecnico nuovo comune vicino a2K/8K secondoM, conteggi reali registrati per ogni tokenizer, nessun padding artificiale. Un warmup escluso per lunghezza, poi2K,8K,2K,8K,2K,8K: tre repliche ciascuna, cap128. ThinkingOFF/specOFF, greedy0, top_p1/top_kdisabilitato, penaltyneutre. Output naturale<128 è SHORT_OUTPUT, senza aggiunte. I timing non descrivono la latenza delle risposte ragionate e non sostituiscono PERF-BASELINE-001.

Zero riuso prefill verificato dai contatori di ogni richiesta; workingKV intra-request è normale. Nessun download/hash/build/profiler invasivo durante queste misure. MemAvailable, VmSwap, fault, I/O e sysfsGPU sono snapshot, non picchi continui o prova di assenza di throttling. Grandezze UMA sovrapposte non vengono sommate.

## Finestre, budget e restore

OrdineQ→restore→M→restore→D→restore→O→restore. Un caricamento principale per profilo. Ciascuno:6sanityON,12casiON,2warmupOFF+6misureOFF,6sanityON, stop dei soli worker del run e restoreK2 verificato. Errori semantici del pannello non interrompono la raccolta. Sanityfail,OOM,corruzione,guasto collector o rischio per il residente fermano la finestra. Nessun retry semantico. Un eventuale problema di packaging prima del pannello resta soggetto al solo intervento circoscritto del mandato, con nuova identità; nessuna ripetizione silenziosa.

Timeout di richiesta pannello:cap/2+300 secondi; sanity1200; engine900. Worktimeout55000,workerruntime55120,supervisor57040,stopworker120,stopsupervisor1350,restore1200,quiesce720 secondi. Dimensionamento conservativo su(73728+13312+1024)/2tok/s con load,prefill e margine; i3.417 storici servono soltanto alla pianificazione, non sono un risultato nuovo. Nessuna durata infinita o estensione opportunistica.

Il runner mantiene compute/runlock, unità transienti, InvocationID, cause iniziali ed ExecStopPost. Gli originali qualificati sono conservati in qualified-002; gli adattamenti aggiungono admissionread-only, protezione del doppio dispatch e attesa di ENTRAMBI i worker. Un rank già terminato con0 non rende completa la coppia. Cleanup non fa reset-failed e non usa pkill. Fermare una unità attiva richiede InvocationID uguale alla ricevuta del proprio run. PeerUNKNOWN o altri owner bloccano il restore anziché essere chiamatiOFF.

Il restore salva controller/owner/release/rank0/rank1/pairedHTTP200 e assenza delle unità/PID propri. K2 non è E1. Gli EngineCore dei cgroupDS41 dopo il restore sono residenti legittimi, non residui da uccidere. Una finestra bloccata prima di aver sospesoK2 non esegue transizioni di ripristino inutili. Un timeout della chiamata on viene riconciliato, non redispatchato.

## MTP: blocker statico circoscritto

Mapping del sidecar verificato CPU:65536 ID univoci, non negativi, nell’intervallo del vocabolario target. Le sei fixturegreedyOFF/ON sono predisposte prima dei modelli e comprendono contesto oltre microbatch.

Tuttavia il commit selezionato disabilita i controlli per-request speculative.n_max con #if0 in server-schema.cpp; speculative type rimane globale e POST/props non espone opzioni. Inviare speculative.n_max=0 nel payload non provaOFF. La sequenzaOFF/ON e le successive misureOFF/ON, entro il solo caricamento aggiuntivo autorizzato e dopo il gate di equivalenza, non è attuabile tramite quel contratto. StatoMTP=BLOCKED_STATIC_CONTROL_CONTRACT: nessuna speculazione viene eseguita né conteggiata come qualificata. Non si aggiunge una patch numerica, un caricamento nascosto o un secondo sidecar. Il confronto dei quattro target con specOFF può proseguire.

## Congelamento e consegna

Prima delle finestre: copie complete dei nostri sorgenti effettivi, validator/test, configurazioni, piani e input, tokenizer, reference, rubriche, definizioni metriche, protocollo e manifest. source-SHA256SUMS non include se stesso; preparation.json lega l’indice al commit preparatorio senza hash circolari. Il peer riceve e verifica gli stessi file necessari e le versioni/binaryhashO/D. I worker dimostrano path/hash dei moduli importati dal frozen tree.

REPORT.md,summary.json,paired-results.jsonl e indice raw derivato sono prodotti dallo stesso evaluator congelato. Le risposte originali rimangono nei run e in copie con SHA. Il ricalcolo CPU--check deve essere realmente eseguito prima di dichiararloPASS. Gli artefatti preregistrati non vengono cambiati dopo le risposte.

Consegna obbligatoria: profili e famiglia/caso, incompleti/tecnici/critici, tutti i tempi, token disponibili, misureengine separate, memoria/nodi, MTPblocker, restore reale, sourcecompleteness, matrice statica di cooperazione sulla stessa richiesta e UNA prossima azione non eseguita. Replica di servizio, sharding di capacità, prefill a blocchi e HaloPipe non sono sinonimi. Nessun port o carico distribuito nuovo oltreD/O. Commit locale dei soli file pertinenti, documenti cluster aggiornati con snapshot preservati, nessun push/deployment.
