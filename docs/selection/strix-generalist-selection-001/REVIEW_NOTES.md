# Lettura dei risultati terminali del nuovo lotto

Queste note descrivono i raw del lotto STRIX-GENERALIST-SELECTION-001. Non modificano il punteggio, il parser, gli expected, i cap o le risposte. Gli addenda di esecuzione erano congelati prima degli output interessati; il postprocessore CPU riconcilia soltanto quelle identita.

## Risultato effettivamente valutato

Q e D hanno dodici risposte ciascuno. Q: tre PASS, otto INCOMPLETE_OUTPUT_CAP, un FAIL_FORMAT. D: tre PASS e nove INCOMPLETE_OUTPUT_CAP. Due successi sono comuni (DATA-IT e SCI-IT); il terzo e OPS-EN per Q, OPS-IT per D. Il totale uguale non dimostra equivalenza ne identico comportamento.

Tutti gli otto incompleti Q e i nove incompleti D hanno zero caratteri di risposta finale. Il ragionamento non e stato chiuso entro i cap4096/8192; non esiste un programma finale da classificare come errato nei casi CODE. Q conserva55807 token reasoning e1026 token finali nativi; il totale56841 comprende inoltre otto token di controllo. Per D i60783 token sono il totale nativo: conteggi reasoning/finale separati e ID generati nativi non sono esposti, quindi rimangono null. Il testo reasoning e il contenuto finale sono separati dall'API nativa.

OPS-IT di Q termina naturalmente e contiene un oggetto dentro un blocco Markdown ```json. La richiesta imponeva JSON puro: il FAIL_FORMAT e corretto. Il corpo dell'oggetto coincide con l'oggetto della risposta D independently-PASS; questa osservazione spiega il formato, ma NON assegna a Q un PASS corretto automaticamente. Nessun fence e stato rimosso nella valutazione.

## Due sanity diversi, due pannelli non inviati

M definisce clamp con un'assegnazione e senza return; tutti e quattro i test restituiscono None. Cinque altri sanity PASS. E un errore funzionale del programma di ammissione, non una prova isolata della perdita dovuta alla IQ2.

O risponde al sanity JSON con i valori alpha7/beta blue corretti, ma dentro fence Markdown. Gli altri cinque sanity, incluso clamp, PASS. E un errore di formato, non un errore dei valori e non una prova di corruzione del runtime.

Entrambi violano il gate preregistrato all-six. Per M/O i dodici task e i benchmark sono NOT_RUN. Non descrivere M/O come0/12 ottenuto in un pannello eseguito. Le sei ricevute O per rank coincidono in input, output, testo e terminazione; la voce automatica peer FAIL_OR_PARTIAL deriva dal conteggio6 invece di32, non da una divergenza fra rank. La verifica completa del prefisso realmente raccolto e in delivery/request-prefix-audit.json.

## MTP e recupero D: errori del collector, non limiti dei modelli

L'addendum ha risolto documentalmente il vecchio problema del toggle HTTP prevedendo avvii separati OFF/ON. Ma il collector OFF ha cercato un campo /props inesistente, prima delle sei reference; il vero campo params["speculative.types"] valeva none. Q principale ha completato i suoi32 record ed e stato ripristinato, ma mancano le continuazioni OFF. Nessun confronto MTP e nessun guadagno MTP sono stati misurati. Il limite e del nostro collector e del budget residuo di caricamenti, non del supporto Vulkan/MTP. Non si recupera con un nuovo load automatico.

D-001 era caricato ma attendeva /health inesistente. Zero richieste erano state inviate. L'unica correzione di packaging consentita ha sostituito la readiness con /v1/models controllato, congelando nuovi nomi di run/unit prima di D-002. Tutte le dodici risposte D provengono da D-002, senza retry semantico; D-001 rimane costo di setup conservato.

## Misure e decisione

Le dodici latenze complete comprendono successi, errori e incompleti: Q1883.163934 secondi, D4054.679925 secondi. I successi non sono gli stessi tre task: non leggere i rispettivi tempi aggregati dei soli successi come un A/B sul medesimo sottoinsieme. Q e piu rapido in tutti i dodici tempi appaiati registrati, ma3/12 non e una qualifica generalista e un unico campione non misura la varianza.

I benchmark motore sono thinking OFF/greedy e separati dalle risposte reasoning sampled. Il prompt-time Q include il primo campionamento; il decode Q e post-first-token. D espone rate totali arrotondati dai log, incluso il primo token. Nessun rapporto fra questi decode viene proclamato esatto. M/O non hanno benchmark nuovi; nessun vecchio TPS e usato per riempire quelle celle.

CODE, MATH e DOCS: nessuna risposta finale Q/D entro il budget. DATA e SCIENCE: un successo su due per entrambi, non una qualifica dell'intera famiglia. OPS: un successo su due per entrambi, su casi differenti. M/O non valutabili su tutte le famiglie. Nessun candidato generalista viene promosso; non e una graduatoria dell'intelligenza pubblica dei modelli. Nessuna violazione critica preregistrata osservata nelle risposte valutate e nessuna esecuzione reale delle azioni proposte; l'assenza di risposte/violazioni non certifica sicurezza.

Lo storico Qwen e stato riusato per pin, loader/PLE, limite delle reference MTP e distinzione fra reasoning completo e codice senza finale. Non e stato rigiocato o sommato a questi risultati. La decisione sul secondo nodo rimane statica in COOPERATION.md: nessun port HaloPipe prima di una configurazione capace di completare i task nel budget.
