# QUALITY-HOLDOUT-002 — note di lettura della consegna

Queste note interpretano i risultati del valutatore preregistrato. Non cambiano casi, expected, schema, parser, scoring o verdict; non correggono gli output e non costituiscono un nuovo esperimento. Fonti: `summary.json`, `paired-results.jsonl`, `expected.jsonl` e risposte native archiviate in `evidence/`.

## Esito e formato

A: 9/18 PASS e 9 FAIL_SEMANTIC. B: 12/18 PASS e 6 FAIL_SEMANTIC. Nove successi comuni, sei fallimenti comuni, tre casi A FAIL/B PASS (JSON-01, JSON-04, CONSTRAINT-02); nessun A PASS/B FAIL.

Tutte le 18 risposte di ciascun braccio superano parsing e schema/tipi. Gli errori qui osservati non sono JSON non parsabili: riguardano regole del compito, ordine di liste, valori, precedenze, calcoli e vincoli. Le dimensioni diagnostiche positive non trasformano un caso FAIL in PASS.

## JSON — distinguere errore di ordinamento e contenuto

**JSON-01, A:** i quattro oggetti spedizione contengono i valori corretti per il rispettivo order_id e i totali sono corretti (22 unità). La lista mantiene invece l’ordine 0007, 0100, 0012, 0003, anziché l’ordine lessicografico richiesto 0003, 0007, 0012, 0100. Le molte differenze per indice mostrate dal report automatico derivano da questa permutazione: non vanno descritte come altrettanti errori indipendenti di cliente o contatto. Il FAIL_SEMANTIC resta, perché l’ordine degli elementi è parte del contratto. Nessun riordino viene applicato per il punteggio. B PASS.

**JSON-02:** A cambia enabled di dev-0001 da false a true benché la patch non includa quel campo; inoltre la lista changed di dev-0006 non è ordinata come richiesto. Il suo enabled_count=3 non corrisponde ai quattro true emessi. B ricostruisce correttamente i dispositivi, ma dichiara enabled_count=2 invece di 3. Entrambi FAIL.

**JSON-03:** entrambi scelgono e06 per K-004 invece di e09, che ha timestamp più recente a revisione e canale pari. B sceglie inoltre e11 anziché e10 per K-005, perdendo il tie-break sull’event_id minore. I totali delle quantità attive risultano 16 per A e 9 per B, anziché 23. Nessuna riscrittura della precedenza.

**JSON-04, A:** per L5, gross352 meno discount88 dà net264; la restituzione di una unità su quattro richiede refund66 e remaining198. A dichiara refund198 e remaining166: è errato sia rispetto ai dati sia rispetto all’identità tra i suoi campi. Il payable è 1867 anziché 1899. B PASS. La soluzione letterale era stata verificata prima dei modelli con Decimal/ROUND_HALF_UP.

**JSON-05:** A accetta le righe3 (disabilitata),4 (ID già accettato) e6 (qty0), che andavano scartate. B accetta anch’esso3 e6, e scarta erroneamente8 come duplicato dopo che la precedente riga2 con lo stesso ID era stata rifiutata per tipo. Il totale accepted_qty=9 di B coincide con l’atteso, ma su record diversi: il totale da solo non prova correttezza. Entrambi FAIL.

**JSON-06:** entrambi PASS sul controllo dei cinque prerequisiti indipendenti e sui totali di rilascio. Non è stata osservata la violazione critica preregistrata di falso rilascio.

## EVIDENCE — perimetro effettivo del 6/6

Entrambi PASS nei sei fascicoli, con 32 claim richiesti per braccio: valori e citazioni esistenti, pertinenti e sufficienti secondo gli insiemi congelati. Il risultato include NOT_RUN distinto da PASS, permesso revocato distinto da test tecnico riuscito, informazione assente conservata null, intervalli mancanti distinti da escursioni confermate e ipotesi distinta da causa provata.

**Limite importante:** ogni fascicolo conteneva anche un riepilogo consolidato firmato, esplicitamente ammesso come alternativa alle fonti primarie per i claim coperti. Entrambi i modelli lo citano per tutti i 27 claim coperti dai riepiloghi; i cinque campi assenti non coperti vengono citati ai rispettivi registri completi. Questo è un risultato positivo di estrazione e citazione da fascicoli chiusi con autorità e consolidamento dichiarati. Non isola la capacità di ricostruire tutte le conclusioni dalle sole fonti primarie senza riepilogo e non misura verifica documentale aperta su fonti reali.

La decisione preregistrata consente soltanto una proposta di pilot circoscritto e supervisionato, in questo perimetro. Non è stato avviato alcun pilot. I controlli con expected completi sono strumenti del benchmark, non un giudice semantico di produzione già implementato.

## CONSTRAINT — vincoli e totali distinti

| Caso | A | B | Riferimento indipendente |
|---|---|---|---|
| 01 | PASS | PASS | M01,M03,M05,M07,M09; costo16, rischio5, valore31 |
| 02 | N2,O1,P1,S1: costo reale13 oltre budget12; manca coverage format-B; costo dichiarato11 | PASS | N1,O1,P1,S1; costo12, rischio4, valore27 |
| 03 | Percorso ammissibile S,B,P,D,Q,T ma perde il tie-break lessicografico; costo7/tempo8 dichiarati contro9/11 reali | S,B,P,C,Q,T perde il tie-break sul rischio; costo8/rischio1 dichiarati contro9/2 reali | S,A,P,D,Q,T; costo9, rischio1, tempo11 |
| 04 | Sceglie rischio1 anziché il minimo0; dichiara costo7/tempo8 contro9/10 reali | Sceglie il percorso ottimo, ma dichiara costo11/rischio1/tempo12 anziché10/0/11 | U,H,K,N,M,Z; costo10, rischio0, tempo11 |
| 05 | Doppia occupazione W-A slot2 con J4 e J5; costo10 dichiarato contro11 reale | J3 e J4 simultanei, contro il vincolo different_slot; costo10 dichiarato contro11 reale | Piano costo9 e makespan3 riportato in expected.jsonl |
| 06 | PASS | PASS | INFEASIBLE: B,C,D richiedono W-A nei soli slot1/2, tre job obbligatori per due posizioni |

B in CONSTRAINT-04 non perde la scelta del percorso: perde il contratto sui totali. Il percorso non viene sostituito e i numeri non vengono corretti per concedere un PASS. Per CONSTRAINT-05 i due piani falliscono vincoli diversi: non attribuire a B il doppio booking osservato soltanto in A.

Le violazioni di questi piani sono errori semantici conteggiati; non vengono rinominate retroattivamente violazioni critiche. I predicati critici sono soltanto quelli preregistrati. Nessun piano è stato eseguito sul cluster.

## Decisioni e contenimento

JSON: per entrambi, contenere gli errori osservati prima di proporre un pilot della famiglia. Parsing e schema possono essere controllati a runtime, ma non bastano: servono regole di trasformazione, precedenza, ordinamento e ricalcolo sui dati reali.

EVIDENCE: solo proposta di pilot supervisionato su fascicoli strutturati e autorità/consolidamenti espliciti. ID, presenza di citazioni, ambito e cutoff sono controlli implementabili sui dati; pertinenza e sufficienza semantica su documenti nuovi richiedono ancora un componente dedicato e/o revisione. Nessun deployment realizzato.

CONSTRAINT: per entrambi, contenere ammissibilità, totali e ottimalità prima di un pilot della famiglia. Un checker di ammissibilità o un solver esterno può individuare/rifiutare un errore; sostituire la risposta con la soluzione del solver sarebbe un trattamento diverso, non il risultato di questo lotto.

Nessun difetto di fixture dimostrato nella revisione dei fallimenti; nessun CASE_INVALID aggiunto. Le famiglie erano scelte alla luce degli errori001: nuovo holdout per istanze, non campione cieco rappresentativo. Non sommare questi 18 casi ai precedenti24, né leggere il 9/18 contro12/18 come percentuale generale di capacità conservata. Effetto della sola quantizzazione non isolato; equivalenza generale non stabilita; nessuna promozione.
