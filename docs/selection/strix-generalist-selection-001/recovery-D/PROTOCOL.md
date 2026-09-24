# D: singola correzione di packaging prima del pannello

Autorizzazione: mandato STRIX-GENERALIST-SELECTION-001, sezione7, una correzione di packaging prima dell'inferenza del pannello con nuova identita e freeze. Non e tuning, modifica numerica, retry semantico o riapertura di una campagna DS4 storica.

## Causa osservata e primo tentativo conservato

`generalist-selection-001-D-001` aveva E1 effettivamente caricato, TP2 collegato e API in ascolto dalle11:03:23 del24settembre2026. Il collector originale attendeva `/health` con status=ok, ma il binario E1 non espone quel percorso. Ricevuta reale alle11:14:51: `/health` HTTP404 unknown endpoint; `/v1/models` HTTP200 list con unico modello deepseek-v4.1-flash e context_length16384. Nel run non esiste alcuna directory requests o raw-results.jsonl: nessun sanity, task o benchmark e stato inviato.

L'arresto e stato richiesto soltanto al supervisor di quel run, verificato dall'InvocationID fc1b2de966c14058a8e629179516d1bb. Il suo ExecStopPost originale esegue stop dei propri due processi e restore K2. `setup-evidence.json` e `stop-intent.json` conservano causa e ambito. Il result raw INTERRUPTED e i tempi dell'intero tentativo rimangono visibili; non viene riscritto come successo.

## Unico recupero ammesso

Nuovo run: generalist-selection-001-D-002. Nuove unit supervisor/rank0/rank1 terminano002. Restano invariati binari E1, GGUF Q2, native Engram, TP2/TCP, porte, API, context16384, sampling, input renderizzati e tokenizzati, sanity, dodici task, warmup/benchmark, limiti di lavoro e restore.

Il solo cambiamento funzionale e la readiness: GET /v1/models, con object=list, esattamente un modello, object=model, id=deepseek-v4.1-flash e context_length16384. Non basta HTTP200 o una porta aperta. Il test CPU usa il payload REALE salvato, non un mock con lo schema inventato. La seconda lettura models rimane documentale, non una generazione. Il corpo del collector da checks/sequence fino alla valutazione e identico al sorgente originale.

Le modifiche restanti sono solo identita di run/unit e destinazione server-trace.log del nuovo run. Gli strumenti di admission conservano integralmente i controlli su owner, residenti, lock, porte, peer e restore. Il vecchio run deve essere terminale e ripristinato, con zero richieste confermate, prima del nuovo dispatch. Nessuna modifica in-place dei74file originali o dei15file dell'addendum Q/MTP.

I file nuovi hanno indice SHA e commit locale propri prima del recupero. Sul peer non serve cambiare il runtime o il sorgente del worker: si usa lo stesso ds4 binario gia verificato, con nuova unita e nuovo GS_RUN_DIR. Per ogni nodo la provenienza del binario e il risultato di caricamento restano registrati.

## Gate e consegna

D-002 e l'unico tentativo di packaging aggiuntivo. Un suo errore del modello, del collector o di sistema viene conservato e non genera automaticamente un terzo run. I task vengono inviati una sola volta, solo dopo il sanity positivo. Dopo il suo restore, O puo procedere usando D-002 come predecessore effettivo; D-001 resta un costo di setup separato, non viene contato come pannello fallito.

Il postprocessore CPU deve verificare la provenienza autorizzata del nuovo adapter e run, mantenendo il medesimo record_audit e validator semantico originali. I dati vecchi non vengono corretti o sovrascritti e nessuna risposta viene scelta best-of. Il recupero non sana il diverso blocco MTP: mancano ancora le reference OFF e non si ricarica Q.
