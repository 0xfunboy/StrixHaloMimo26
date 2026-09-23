# QUALITY-RETENTION-001 — protocollo preregistrato

Mandato esecutivo dell’utente del 23 settembre 2026. Allegato letto integralmente: `StrixHaloMimo26_QUALITY_RETENTION_001_MANDATO(1).md`, SHA256 `958e0f32a76a5525da22a51e80f5f638fbf64191823397e6506fc53f393b13e3`. Il file allegato è la fonte del mandato; questo protocollo ne specifica l’implementazione. Nessun risultato A/B è stato osservato durante la preparazione.

Base locale: commit `fb432c37f96c4514e763bb49f57614d9696efe79`, branch `perf/mimo26-strix`, repository `/home/funboy/StrixHaloMimo26`. PERF-BASELINE-001 rimane terminale PARTIAL_ENGINE_DECODE_ONLY; nessun benchmark o recupero storico riaperto.

## Domanda e limiti

Valutare se le due configurazioni complete risolvono compiti locali rappresentativi, rispetto a specifiche e test indipendenti. A è mixed IQ2/Q8 Baekpica su un solo Strix; B è originale Xiaomi FP8/MXFP4 su due Strix TP2. B non è ground truth, non è BF16 integrale e non definisce le risposte ammissibili. Cambiano runtime e distribuzione: nessuna attribuzione causale alla sola quantizzazione, nessuna percentuale generale di capacità conservata, non inferiorità statistica o equivalenza generale.

## Pannello e oracoli

24 fixture sintetiche autonome, esplicitamente distinte da log o misure reali del cluster. Quattro casi per ciascuna famiglia: Codice, Debugging, Dati strutturati, Documenti, Diagnosi e pianificazione, Ragionamento vincolato. Dodici prompt italiani e dodici inglesi. Ordine congelato: CODE-01…04, DEBUG-01…04, STRUCT-01…04, DOC-01…04, OPS-01…04, REASON-01…04. Identico ordine per A e B.

I messaggi, prompt renderizzati e liste ID effettivamente inviate sono in `cases.jsonl`; soluzioni di riferimento, test positivi/negativi e regole critiche in `expected.jsonl`. I modelli ricevono soltanto i prompt dei casi: non i test nascosti, le soluzioni di riferimento, i validator o altre risposte. Tutti gli expected sono stati scritti e verificati prima dei run. Knapsack e percorso vincolato sono risolti indipendentemente per enumerazione; gli altri calcoli e le funzioni hanno specifiche esplicite e test. Le risposte A/B non possono essere usate per adattare casi o validator.

Gli input di questo pannello sono volutamente brevi ed espliciti: 126–243 token renderizzati per caso nella preparazione corrente, non un test di contesto lungo o coding su repository. La complessità è nei contratti e nei casi limite, non nella lunghezza del prompt.

## Budget e arresto

Otto casi Codice/Debugging: cap 1024 ciascuno. Sedici altri casi: cap 512 ciascuno. Totale massimo pannello: **16.384 token di output per braccio**, sotto il tetto autorizzato di 24.576. Le soluzioni indipendenti occupano al massimo 153 token; il budget include ampio margine. Input effettivo ≤2048; input + cap + margine32 ≤4096. Non si cambia il cap in seguito ai risultati.

Una sola generazione per caso/braccio. Temperature0, seed1, penalità ripetizione1, presence/frequency0, thinking OFF, EOS naturale, niente stop aggiuntivi o ignore_eos. Se si raggiunge il cap, anche con un oggetto apparentemente completo, stato conservativo INCOMPLETE_OUTPUT_CAP. Una risposta naturale più breve è COMPLETE, non SHORT_OUTPUT. Nessun best-of, retry semantico, riparazione, completamento con secondo prompt o esclusione selettiva.

Timeout per richiesta preregistrato: max(240, cap/2+180) secondi, cioè 436s per cap512 e 692s per cap1024. Sanity: 300s per richiesta. A: load massimo600s, lavoro7200s, worker7320s, supervisor9240s. B: lavoro14400s, worker14520s, supervisor16440s. Quiesce720s, stop worker90s, restore1200s. B è dimensionato sul cap totale con assunzione prudente di pianificazione 2 token/s, più prompt, caricamento, sanity e margine: non è una nuova misura di velocità. Timeout finiti, nessuna estensione opportunistica. Il timeout HTTP A è affiancato dal controllo wall; B usa allarme per richiesta più controllo elapsed e timeout globale dei worker. Nessun rinnovo dei timeout dopo la risposta.

## Input e percorsi di richiesta

A: nuovo collector `adapter_a.py`, endpoint nativo `/completion`, stream=false, prompt come ID congelati, return_tokens=true, return_progress=false, cache_prompt=false. I sanity usano lo stesso endpoint e gli stessi parametri. `/tokenize` del runtime verifica preventivamente tutti i prompt contro gli ID congelati; il risultato nativo non riecheggia gli input ID, ma conserva prompt/n conteggi e gli ID della richiesta sono salvati prima dell’invio. Output nativi: array tokens e tokens_predicted, con verifica contro predicted_n. Non si ricostruiscono ID emessi dalla ritokenizzazione del testo.

B: nuovo collector `adapter_b.py`, stessa architettura offline LLM.generate TP2 qualificata, stessi ID congelati, input ID nativi riecheggiati e controllati, token_ids nativi dell’output e oggetto RequestOutput completo serializzato. Entrambi i rank salvano le proprie risposte e i propri controlli. NODE02 viene confrontato con NODE01 per identità di prompt e output, senza contarlo come una completion extra.

Nessun client SSE, qualificazione TTFT o correzione del vecchio collector. Cache di prefill riusata pari a zero per ogni richiesta: A native cache_n=0 e prompt_n/tokens_evaluated uguali all’input; B num_cached_tokens=0. Il tokens_cached di contesto finale A non è trattato come riuso. Nessuna memoria fra casi, nessuna cache globale svuotata.

## Configurazioni e congelamento

A mantiene llama.cpp `58367713a6935c0810103378144008df32e3d5db`, binary SHA256 `5898a81b08e919c507e09fb4252265c5ee3b8373cef13edc475cf267415cd8c7`, HIP/gfx1151, context4096, batch512/ubatch128, uno slot, all GPU layers, split none, no continuous batching, FA auto, quattro shard già presenti. Revision mixed `b3794b22b6276f8120c340f52639f5eaa354a3fd`. Porta locale temporanea18342.

B mantiene originale revision `5711b268169967567844e1e560e8a3966da959b1`, vLLM `0.1.0rc2.dev9+g9255fd9fb9.rocm100`, Torch `2.13.0+rocm10.0.0`, Transformers `5.16.1`, TP2/PP1, text-only, eager, triton_unfused, context4096, KV1073741824 byte/rank, una sequenza, batch512, prefix caching OFF. Patch QKV SHA256 `eeb66fefbf1b63459e5712c031399f2d24d9ac05956c97b4e979ad03b901be72`. Environment qualificato, incluso il percorso di import AMD SMI, senza mutare il virtualenv. Rendezvous29641 su USB4 esistente.

Tutti gli script nuovi, incluse preparazione, adapter, parser, validator, sandbox, test, launcher e valutatore, vengono copiati in `sources/`. Il runner qualificato e cleanup sono copie byte-identiche, non reimplementazioni. Copie dei tre script lifecycle residenti sono archiviate per audit e i file esterni realmente usati restano vincolati dai loro hash: non vengono modificati. Versioni e hash dei binari/dependenze pertinenti sono nel manifest. Nessun peso, segreto o ambiente completo incluso nell’archivio.

`source-SHA256SUMS` indicizza sorgenti/casi/expected/configurazioni/protocollo/manifest e ricevute CPU; non include se stesso. Il manifest non contiene il proprio hash. Un commit locale di preparazione è creato prima di qualunque load; `preparation.json` registra successivamente tale commit e hash dell’indice, senza cicli. I file frozen non sono più modificabili nel corso della campagna. Stessa copia verificata sul peer prima di A. Lo scratch preesistente non entra nei commit.

## Validator indipendenti e isolamento

JSON: un unico documento JSON, opzionalmente un singolo fence json; chiavi duplicate, costanti NaN, testo extra, fence incompleti, campi/tipi errati non sono ammessi. Bool e interi sono distinti. Ordine delle chiavi oggetto irrilevante; ordine e valori degli array rispettano la specifica. Le condizioni mancanti nei documenti restano null/UNKNOWN come indicato nel prompt.

Codice: Python3 in chiaro o un unico fence python/python3; funzioni, helper locali e built-in ordinari, senza import/classi/decorator/I/O/exec/eval/introspezione/attributi privati. Il codice generato NON è eseguito sul nodo host. Viene inviato via stdin al sandbox Podman rootless esistente con immagine immutabile `a58caff183f8eb10c84fce3d3eb8496e684411369848a77bfcf0af9074cc16c4`, pull=never, network=none, nessun mount host, root read-only, uid65534, capability eliminate, no-new-privileges, nessuna GPU, memoria256MiB, massimo32 processi. All’interno: CPU3s, spazio indirizzi192MiB, file1MiB, fd64. Wall timeout15s; viene rimosso solo il container del validator identificato con UUID. L’harness fidato applica AST guard, esegue i test indipendenti e verifica che gli input non siano mutati. Limiti CPU/runaway e isolamento sono testati prima dei modelli. I tool dei piani sono soltanto JSON: mai azioni reali.

Stati: PASS; FAIL_SEMANTIC; FAIL_FORMAT; FAIL_CODE_TEST; INCOMPLETE_OUTPUT_CAP; TECHNICAL_ERROR/TIMEOUT; VALIDATOR_BLOCKED/NEEDS_REVIEW; CASE_INVALID. Un caso non eseguito resta NOT_RUN esplicito, non viene conteggiato come errore semantico o omesso. Errori di setup del sandbox sono VALIDATOR_BLOCKED, non errori del modello. Violazioni del formato/schema restano distinte dagli errori di valore. Una specifica/validator dimostrata ambigua o difettosa comporta CASE_INVALID per entrambi, senza modificare prompt e rilanciare il perdente.

## Violazioni critiche preregistrate

Le regole per caso sono nei due JSONL: retry non autorizzato/non idempotente in DEBUG-03; campi azione/abilitazione indotti da nota non fidata in STRUCT-03; disponibilità inventata nonostante conflitto in DOC-02; test funzionali mai fatti dichiarati PASS in DOC-03; retry/mutazioni su job di altro owner in OPS-01; restore con peer sconosciuto in OPS-02; azioni non ammesse, release errata o restore prima di verify_off in OPS-03. Le violazioni osservabili sono conteggiate separatamente per A e B. Una risposta malformata non è interpretata arbitrariamente come un’azione: resta FAIL_FORMAT. Regressione critica: violazione A con B PASS; le violazioni critiche di entrambi sono comunque mostrate e non rese accettabili dall’accordo.

## Supervisione ed esecuzione

Ordine: A → restore verificato → B → restore verificato. Run ID nuovi, mai riutilizzati. Un solo caricamento per braccio; sei sanity preflight,24 casi,sei sanity postflight. Nessun warmup o replica prestazionale. Ogni richiesta salva intent IN_FLIGHT, payload, risultato completo atomico e hash prima di quella successiva.

Il dispatcher verifica identità, ownership/invocation, K2 READY/idle, release, hash, porte, lock e assenza di run/supervisor già esistenti. I transient supervisor riusano i byte del runner qualificato con compute lock, registry/eventi, worker limitati e ExecStopPost qualificato; cambiano soltanto nomi e budget finiti di questa campagna. Una disconnessione MCP impone lettura del run esistente, non redispatch. Fallimenti semantici restano nel pannello; problemi tecnici/OOM/collector fermano la finestra e attivano il cleanup. Sanity pre fallito impedisce il pannello; sanity post fallito impedisce la qualifica del braccio.

Residente da ripristinare: K2 dspark-k2-gfx1151, release `5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513`, tramite il suo controller esistente. Non E1 storico. B non parte finché A non ha24 risultati e sanity PASS e restore storico/live verificato. Nessuna operazione su altri owner, reset/clean o modifiche delle release DS41.

## Analisi e consegna

Il valutatore congelato ricalcola CPU-only tutte le risposte mediante gli stessi oracle/validator. Object B non è un giudice. Tutti i24 casi rimangono nel denominatore per braccio. Coppie valutabili: entrambi PASS o un FAIL semantico/formato/codice; tutti gli altri stati sono visibili separatamente. Tabella appaiata, conteggi per famiglia, regressioni A FAIL/B PASS, casi A PASS/B FAIL, fallimenti comuni e violazioni critiche. Markdown e JSON generati dalla stessa base. Nessuna percentuale di capacità rispetto all’originale.

Comando implementato di ricalcolo, da verificare sui risultati prima della consegna:

```bash
cd /home/funboy/StrixHaloMimo26
PYTHONDONTWRITEBYTECODE=1 python3 docs/mimo26/quality-retention-001/sources/evaluate.py --root docs/mimo26/quality-retention-001 --check
```

EXPERIMENT_COMPLETION è separato dal successo dei casi. I tempi incidentali sono diagnostici, non aggiornano PERF-BASELINE-001. GENERAL_QUALITY_EQUIVALENCE=NOT_ESTABLISHED; QUANTIZATION_ONLY_EFFECT=NOT_ISOLATED; LONG_CONTEXT/CONCURRENCY/MTP_DFLASH=NOT_EVALUATED; PRODUCTION_PROMOTION=NOT_PERFORMED. Una criticità osservata impedisce l’uso autonomo in quel compito; anche24/24PASS giustificano al più una proposta di pilot supervisionato.

Consegna: report/summary/paired/raw index, originali intatti, indici hash, ricevute restore e live finale con owner/release/invocation/health/no residui/lock rilasciato, handoff e commit locale soli file pertinenti. Nessun push, PR, deployment, nuovi benchmark, tuning o nuove campagne. Il passo successivo resta soltanto proposto.
