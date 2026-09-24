# MTP: blocco reale del collector OFF, non del modello o del toggle di avvio

Osservazione originale: 2026-09-24T10:49:02+0200, nel run `generalist-selection-001-Q-001`, dopo tutte le32 richieste principali e sanity postflight6/6.

Il collector aggiuntivo ha letto `/props` e cercato `default_generation_settings.speculative`. Nel payload reale questo campo non esiste; la modalita e esposta in `default_generation_settings.params["speculative.types"]`, con valore `"none"`. Il comando effettivo del processo era target-only senza `-md`. Non si tratta di una prova che Qwen non supporti MTP: e un errore del nostro collector, il cui mock CPU riproduceva la forma attesa anziche quella effettivamente servita dal pin.

Evidenze native:

- `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001/mtp-off/props.json`
- `.../mtp-off-blocker.json`: `RuntimeError:MTP_PROCESS_MODE_UNPROVEN:None`
- `.../load.json`, `.../native-props.json`, `.../sanity-pre.json`, `.../sanity-post.json`

La verifica della proprieta e avvenuta prima del loop delle reference: nessuna completion MTP OFF e stata inviata, nessuna reference esiste da appaiare. Il sotto-percorso contiene il payload `/props`, non risultati di inferenza. Il modello Q principale e stato quindi scaricato normalmente e il suo restore e PASS alle10:53:53+0200. Le32 righe primarie, gli input, i punteggi e i tempi del nuovo pannello restano invariati.

Il campo corretto dimostra documentalmente il target-only del Q gia eseguito; non puo ricostruire le sei continuazioni OFF mancanti. La finestra target principale e consumata. Non si ricarica Q, non si sostituiscono le reference con altri prompt/vecchi modelli e non si aggiunge un secondo caricamento extra per aggirare il budget. Il caricamento MTP ON non e ammesso senza quelle reference; il suo risultato rimane NOT_RUN/BLOCKED_OFF_REFERENCE_COLLECTOR, non FAIL di equivalenza e non un limite fisico di Vulkan o Strix.

Questo blocco e isolato alla fase MTP. M, D e O proseguono secondo il mandato. I file originali e l'addendum pre-output restano congelati; nessun parser, raw o verdict viene riscritto per ottenere PASS. Un'eventuale correzione e nuova prova OFF/ON richiederebbe una successiva autorizzazione specifica e non e eseguita qui.
