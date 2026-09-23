# StrixHaloMimo26 — QUALITY-HOLDOUT-002: preregistrazione operativa

Mandato autorizzato dall’utente il23 settembre2026, allegato SHA256 `b73f9233798296a75f457dd03acb64c4de9aa423c09f107d9e5e00c464e58431` (registro di provenienza in MANDATE.md). Base locale `0e2ae3708beaeec2adf5e993ce2091c2dba4220d`, branch perf/mimo26-strix, repository `/home/funboy/StrixHaloMimo26`.

## Perimetro e preregistrazione

18 casi nuovi sintetici autonomi, sei per JSON, EVIDENCE e CONSTRAINT;3 italiani e3 inglesi per famiglia. Le istanze sono nuove, mentre la scelta delle famiglie è informata dai fallimenti001: non è un campione cieco rappresentativo di tutti gli usi. Non vengono letti altri progetti o dati aziendali per creare le fixture. QUALITY-RETENTION-001 rimane completata, PERF-BASELINE-001 rimane terminale PARTIAL_ENGINE_DECODE_ONLY; nessun benchmark/riparazione/archeologia delle vecchie campagne.

I file cases.jsonl, expected.jsonl, sanity.jsonl, codice completo, parser, validator, schema report, configurazioni, budget e questo protocollo sono conclusi prima dei modelli. source-SHA256SUMS include i loro byte e source-manifest.json, ma non se stesso. Un commit locale di preparazione precede i run; preparation.json lega successivamente quel commit all’indice, evitando hash circolari. Il peer riceve gli stessi byte verificati prima di A. Nessuna risposta A/B è stata letta durante la costruzione delle istanze.

## Casi, riferimenti e significato delle prove

JSON-01: manifesto annidato, quantità filtrate/aggregate e identificativi con zeri iniziali.
JSON-02: patch con distinzione tra assente, null-reset, stringa vuota, zero e false.
JSON-03: registro versionato con precedenza revisione/canale/timestamp/ID e tombstone.
JSON-04: sconti per riga, resi proporzionali, imposte con ROUND_HALF_UP e credito finale.
JSON-05: separazione validi/scarti con precedenza esplicita e deduplica dei soli validi accettati.
JSON-06: cinque guardie indipendenti e conservazione dei totali di rilascio.
Gli expected JSON sono risposte letterali preparate indipendentemente, con invarianti e controesempi per campo. L’aritmetica monetaria letterale è inoltre confrontata con una implementazione Decimal ROUND_HALF_UP separata.

EVIDENCE-01…06: fascicoli multipli su autorità/revisioni/cutoff, ordini accettati e cancellazioni, identità binario-configurazione dopo rollback, autorizzazione revocata distinta da test tecnico, misure corrette con intervalli mancanti, sequenze incidenti distinte da chat non sincronizzate. Ogni claim ha valore atteso, insiemi minimi alternativi di citazioni sufficienti e ID contestuali pertinenti ammessi. Una combinazione è accettata se contiene un insieme sufficiente e soltanto ID pertinenti, senza duplicati; l’ordine non conta. I riepiloghi firmati equivalenti sono ammessi dove attestano esplicitamente il claim. Un ID esistente ma irrilevante, superato o fuori scope non soddisfa il claim. Gli output non sono confrontati letteralmente con B.

CONSTRAINT-01/02: selezione binaria di moduli con gruppi, dipendenze, incompatibilità, coperture e capacità separate. CONSTRAINT-03/04: grafi diretti con checkpoint ordinati, limiti, vertici vietati e ordini diversi degli obiettivi. CONSTRAINT-05/06: assegnazione di job unitari a worker-slot con eleggibilità, precedenze e risorse esclusive. La06 è dimostrabilmente INFEASIBLE: tre job richiedono tre occupazioni del medesimo worker nelle sole due posizioni ammesse. Ogni problema viene risolto prima dei modelli da enumerazione finita e ricerca indipendente con fattibilità/aritmetica codificate separatamente; non sono due chiamate allo stesso helper. Confronto della soluzione migliore e del numero di soluzioni ammissibili. I cinque casi fattibili hanno più soluzioni con obiettivo primario pari, da discriminare con tie-break congelati.

I solutori e tutti gli expected rimangono strumenti del valutatore: i collector forniscono ai modelli solo messaggi e schema pubblico dei compiti, mai le soluzioni, gli elenchi ammissibili, i test o feedback. Nessun giudice LLM. La correttezza di B non è presupposta.

## Budget e input effettivi

Per ogni famiglia quattro cap512 e due cap1024, totale massimo12288 token di pannello per braccio, esclusi sanity. Un output naturale più corto è completo; nessun output viene allungato o completato con altre richieste. Un cap raggiunto implica INCOMPLETE_OUTPUT_CAP, anche se il testo sembra chiuso.

Ogni input effettivo include template e token speciali. Gate hard: input+cap+256<=4096, senza troncamento. I range sono obiettivi indicativi, non gate artificiali: il fascicolo EVIDENCE-03 è2599 token (+39 sul target), CONSTRAINT-06 è771 (-29); le altre istanze rispettano i range indicati dal mandato. Nessun padding. Conteggi completi preregistrati in preflight/tokenization.json. La presentazione JSON del prompt è compatta: sono stati tolti soltanto spazi di indentazione e ridondanze narrative prima del freeze, non dati a runtime.

Prompt/cap/ordine identici nei due bracci. Ordine: JSON-01…06, EVIDENCE-01…06, CONSTRAINT-01…06. Input IDs congelati dal tokenizer locale; roundtrip del testo renderizzato con add_special_tokens=false, senza doppio BOS. A verifica tutti gli input con /tokenize prima delle richieste, B con il tokenizer effettivo e l’eco degli input nativi.

## Pin e percorsi qualificati

A: Baekpica MQ-IQ2-XXS-XS-Q8-MM-BF16 revision b3794b22b6276f8120c340f52639f5eaa354a3fd; quattro shard principali già presenti; llama.cpp58367713a6935c0810103378144008df32e3d5db, binary SHA2565898a81b08e919c507e09fb4252265c5ee3b8373cef13edc475cf267415cd8c7. HIP/gfx1151, context4096, batch512/ubatch128, una sequenza, allGPUlayers, splitnone, no continuous batching, FAauto. Porta temporanea locale18343. Collector adapter_a.py byte-identico al001; /completion NONSTREAMING con ID nativi, return_tokens=true e return_progress=false, cache_prompt=false.

B: XiaomiMiMo/MiMo-V2.6-Flash-RL revision5711b268169967567844e1e560e8a3966da959b1, vLLM0.1.0rc2.dev9+g9255fd9fb9.rocm100, Torch2.13.0+rocm10.0.0, Transformers5.16.1, TP2/PP1, text-only/eager/triton_unfused,context4096,KV1073741824 byte/rank,una sequenza. Patch QKV eeb66fefbf1b63459e5712c031399f2d24d9ac05956c97b4e979ad03b901be72. Collector adapter_b.py byte-identico al001, offline LLM.generate; rendezvous29642. Environment qualificato incluso AMD SMI import path, senza modificare il venv. Runtime kwargs, librerie, build flags, tokenizer e lifecycle hashes nel manifest. Nessun nuovo hashing massivo dei pesi.

Entrambi: greedy temperature0 seed1, penalty ripetizione1, presence/frequency0, ignore_eos=false, thinkingOFF, prompt reuseOFF, speculative/mmprojOFF. Non vengono aggiunti grammar, repair o solver. I token di output sono quelli restituiti nativamente, non ritokenizzati. I timestamp incidentali sono diagnostici, non un benchmark.

I collector A/B e sandbox_inner restano byte-identici; copie originali complete conservate in sources/qualified-001. common.py è una versione minima nuova per campaignID, pubblicazione atomica esclusiva senza sovrascrittura e ricevute degli import effettivi. Il lanciatore cambia solo nomi, percorsi, porte e prerequisito18casi. I worker verificano l’intero indice e dimostrano path/hash dei moduli eseguiti dal frozen tree. Runner e cleanup sono copie byte-identiche di quelli qualificati001, non un nuovo lifecycle.

## CPU, parser e scoring congelati

Parser pannello: un unico JSON senza markdown/prosa. Rifiuta chiavi duplicate, NaN/Infinity e overflow floating non finiti, booleani al posto di interi, tipi inattesi, chiavi extra e campi mancanti. Nessun spelling/type/value repair. Ordine chiavi irrilevante; ordine liste secondo compito. Parsing, schema/tipi, valori e invarianti riportati separatamente. I criteri generali non sono allentati dopo i risultati.

EVIDENCE: distingue valore, esistenza ID, pertinenza, sufficienza, duplicati e copertura per claim. I test CPU coprono combinazioni di insiemi alternativi corretti, ID fittizi, ID esistenti irrilevanti/superati, citazioni assenti/parziali e valore errato con fonti corrette.

CONSTRAINT: schema, ammissibilità e singoli vincoli, totali ricalcolati, veridicità dei totali dichiarati, obiettivo primario, tie-break. Una soluzione ammissibile subottimale non è PASS. I totali del solver non sostituiscono quelli dichiarati dal modello. INFEASIBLE richiede prova dell’oracolo e output vuoto/null previsto dal contratto. Nessun secondo score «corretto col solver».

Stati distinti: PASS, FAIL_FORMAT, FAIL_SEMANTIC, INCOMPLETE_OUTPUT_CAP, TECHNICAL_ERROR/TIMEOUT, VALIDATOR_BLOCKED, CASE_INVALID/NOT_RUN. Un difetto della fixture/scoring emerso dopo inferenza viene registrato per entrambi come CASE_INVALID, senza correggere e rilanciare il caso. Un eventuale case-invalid.json post-hoc può contenere soltanto ID del lotto e motivo esplicito, applicato simmetricamente; non cambia gli expected congelati.

Criticità preregistrate: JSON-06 release=true per lotto che fallisce almeno una guardia obbligatoria; EVIDENCE-03 functional_validation=PASS al posto di NOT_RUN; EVIDENCE-04 export_permission=APPROVED nonostante revoca. Non ogni errore è critico. Le violazioni si contano separatamente per braccio e non attestano sicurezza generale quando assenti.

I sanity sono gli stessi sei casi tecnici separati, copiati byte-identici. Il codice clamp generato viene eseguito esclusivamente nel sandbox rootless Podman pinned a58caff183f8eb10c84fce3d3eb8496e684411369848a77bfcf0af9074cc16c4: no rete/mount host/GPU/credenziali, uid65534,capabilities0,rootread-only,256MiB,32processi,3sCPU,15swall. Nessun exec del codice dei modelli sull’host; i nuovi piani sono solo JSON.

## Finestre seriali e checkpoint

A→restoreverificato→B→restoreverificato. Un caricamento per braccio;6sanitypre,18casi,6sanitypost. Nessun warmup o replica prestazionale. Gli errori semantici non interrompono il pannello; collector/timeout/sanity/GPUfault attivano cleanup e impediscono una qualifica indebita. B non parte senza A completo, sanityPASS e restore storico/live verificati.

Timeout per-case: cap/2+240 secondi, cioè496/752, sanity300. LoadA600. LavoroA7200/B14400,worker+120,supervisor+2040,quiesce720,stopworker90,restore1200. Sono limiti finiti dimensionati prudentemente sul percorso B e sul cap totale, non promesse di durata. Nessuna estensione opportunistica.

Identità, owner/invocation, K2READY/idle, release attiva, lock e porte libere vengono verificati prima delle transizioni. Non si impone un epoch storico. Ogni richiesta salva intent, payload, risultato atomico e digest prima della successiva; gli ID non sono riutilizzabili. Ogni dispatch ha receipt e supervisor con ExecStopPost del cleanup qualificato. Dopo timeout MCP si legge stato/registry/requestID/cgroup e non si redispatcha.

Restoretarget: controller reale della release K2 k2-prefill-5bdfed6, preset dspark-k2-gfx1151, release5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513, solo se confermato dal live. Verifica controller/owner/healthrank0/rank1/paired, assenza dei PID e unità del run, lock liberi. EngineCore in cgroup DS41 sono residenti legittimi: nessun pkill generico. Orari dei controlli conservati separatamente.

## Report e decisione finale

REPORT.md,summary.json,paired-results.jsonl,FINDINGS.md sono generati dalla stessa base canonica. Tutte le18coppie rimangono visibili; i30 record del peer B non sono altre repliche. raw-results.jsonl è un indice derivato dichiarato, con collegamenti ai file originali; copie archiviabili con SHA256 senza modificare i raw.

Decisione per famiglia predefinita: dati incompleti/invalidi impediscono una proposta di pilot sulla famiglia; errori completi osservati richiedono contenimento prima di tale proposta; solo una famiglia senza errori osservati può meritare una proposta di pilot strettamente circoscritto e supervisionato. Non è una soglia di promozione: nessun risultato autorizza uso autonomo, deploy, routing o nuova campagna. L’analisi descrive i contratti riusciti, gli errori precisi e quali controlli sono implementabili a runtime. Il valutatore con expected completi non viene presentato come controllo di produzione già realizzato.

Ricalcolo implementato da verificare sui raw prima della consegna:

```bash
cd /home/funboy/StrixHaloMimo26
PYTHONDONTWRITEBYTECODE=1 python3 docs/mimo26/quality-holdout-002/sources/evaluate.py --root docs/mimo26/quality-holdout-002 --check
```

Richiede percorsi originali e immagine Podman locale per i sanity; nessuna pretesa di portabilità. verification.json registra il PASS del ricalcolo separatamente dai risultati. Le vecchie campagne e lo scratch sono verificati invariati con l’indice d’ingresso. CURRENT aggiornato soltanto secondo AGENTS, con snapshot precedente preservato, singolo record e scheda MiMo; nessun codice/releaseDS41 toccato.

**Fine:** commit locale dei soli file pertinenti e consegna con decisione per famiglia. Nessun push/PR, pilot reale, deployment, tuning, thinkingON, NVIDIA/Vulkan/MTP/DFlash, modifica infrastrutturale, espansionecontext o esperimento successivo automatico. GENERAL_EQUIVALENCE=NOT_ESTABLISHED e QUANTIZATION_ONLY_EFFECT=NOT_ISOLATED, anche se tutti i casi passassero.
