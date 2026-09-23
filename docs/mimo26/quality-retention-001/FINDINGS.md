# QUALITY-RETENTION-001 — lettura dei risultati verificati

Questa nota interpreta i risultati del valutatore preregistrato. Non cambia casi, expected, validator, severità o verdict. Fonti: `paired-results.jsonl`, `summary.json`, `expected.jsonl`, risposte originali archiviate in `evidence/run-A/requests/` e `evidence/run-B/requests/`.

## Esito

Esperimento completato: una finestra A e una B, ciascuna con24 casi e sanity6/6 prima e dopo, restore K2 verificato dopo ogni finestra. Tutte le48 risposte del pannello sono complete con arresto naturale; nessun cap, timeout, errore tecnico o caso escluso. Gli input effettivi coincidono; il prefill riusato è zero. La verifica indipendente dei36 record NODE02 è PASS e non aggiunge repliche al denominatore.

**A mixed:21/24 PASS** (due FAIL_SEMANTIC, un FAIL_FORMAT). **B originale TP2:21/24 PASS** (tre FAIL_SEMANTIC). Le coppie sono20 BOTH_PASS, due BOTH_FAIL, una A_FAIL_B_PASS e una A_PASS_B_FAIL. Le24 coppie sono tutte valutabili. Nessuna violazione critica preregistrata è stata osservata in A o B; nessuna regressione critica.

| Famiglia | A mixed | B originale TP2 |
|---|---:|---:|
| Codice | 4/4 | 4/4 |
| Debugging | 4/4 | 4/4 |
| Dati strutturati | 4/4 | 4/4 |
| Documenti | 4/4 | 3/4 |
| Diagnosi e pianificazione simulata | 4/4 | 4/4 |
| Ragionamento vincolato | 1/4 | 2/4 |
| Totale | 21/24 | 21/24 |

## Regressione osservata della mixed: REASON-03

Il compito chiede una fattura sintetica con sconti, IVA e arrotondamento half-up, in uno schema JSON esatto.

Expected indipendente:

```json
{"net_lines_cents":[537,400],"tax_cents":206,"total_cents":1293}
```

A produce gli stessi numeri corretti, ma usa la chiave **`total_censes`** al posto di **`total_cents`**. B rispetta lo schema. A è quindi `FAIL_FORMAT`, B `PASS`.

È una regressione di conformità dello schema, non un errore aritmetico. Il validator non corregge automaticamente la chiave e non concede il PASS per somiglianza. Un consumatore che richiede `total_cents` non riceve il campo contrattuale.

## Caso favorevole alla mixed: DOC-03

Entrambi classificano correttamente la disponibilità HTTP, il rollback completato e i test funzionali come **NOT_RUN**. Tuttavia B restituisce `evidence.functional_validation=[]`, mentre A cita `["E3"]` come richiesto. E3 dichiara esplicitamente che i test funzionali non sono stati eseguiti.

A `PASS`, B `FAIL_SEMANTIC`: manca la prova documentale richiesta nella risposta B. Non si tratta di una falsa dichiarazione di test superati; per questo non scatta la regola critica preregistrata del caso.

## Errori comuni: REASON-02, selezione con vincoli

Budget8; optimum verificato per enumerazione indipendente: **A+B+E**, costo8, valore17, con tie-break lessicografico preregistrato.

A seleziona **A+C**, costo6, valore13: la scelta è ammissibile ma non massimizza il valore. B seleziona **A+B+C**, costo9, valore20: supera il budget8. Sono due errori semantici diversi; la risposta originale B non viene assunta corretta.

## Errori comuni: REASON-04, percorso con rischio limitato

La soluzione indipendente è **A→C→E→D**, costo5, rischio0. Entrambi scelgono **A→B→C→E→D**: questo percorso ha costo reale5 e rischio1. Ha lo stesso costo minimo ma perde sul tie-break che preferisce rischio più basso.

In aggiunta, A dichiara costo6 e B costo7 invece del costo reale5. Entrambi sono `FAIL_SEMANTIC`: mancato tie-break e somma del costo errata. Non si descrive il percorso scelto come realmente più costoso solo perché il modello ne ha sbagliato il totale.

## Interpretazione operativa

Nel pannello breve e sintetico, entrambi superano tutti gli otto casi di codice/debugging con i test indipendenti nel sandbox, oltre ai quattro casi di dati strutturati e ai quattro piani diagnostici simulati. Ciò non prova la capacità di modificare repository reali o operare servizi in autonomia.

La mixed non mostra un crollo generalizzato su questo pannello, ma la parità21/24 non dimostra equivalenza con l’originale: i fallimenti non sono gli stessi. Il suo errore di schema resta operativo anche con aritmetica corretta. Entrambi richiedono controlli esterni per ottimizzazione vincolata, somme e tie-break; entrambi hanno violato almeno un requisito in quei compiti.

Qualunque uso successivo dovrebbe restare circoscritto e supervisionato, con JSON Schema, unit test o solver deterministici e rifiuto delle risposte non conformi. Questo è un suggerimento, non un deployment o una promozione eseguita. L’assenza di violazioni critiche nei casi simulati non certifica la sicurezza operativa generale.

Il pannello contiene solo126–243 token di input per caso, 12 casi italiani e12 inglesi, con una sola generazione per configurazione. Non sono coperti contesti lunghi, task aperti, uso reale dei tool, concorrenza o distribuzioni rappresentative di tutti i carichi. **21/24 non significa “87,5% delle capacità dell’originale”.** Non è isolato l’effetto della sola quantizzazione, poiché differiscono anche runtime e distribuzione.

## Integrità e replica dell’analisi

Preparazione commit `6c32e7509db1920c2e78c985ff913c8c8d83af18`, fonte congelata prima di A e B. Indice SHA256 `9f60624b3a68269cae973efc239426a285b13e3c7de982dcb3f662c7b0ebf337`. I217 controlli CPU preliminari sono PASS. Il comando `sources/evaluate.py --check` ha ricalcolato gli stessi verdict, i report e l’indice delle risposte senza inferenza, con il medesimo sandbox e senza cambiare i validator.

Restore A completato23 settembre2026 alle13:33:46 Europe/Rome; restore B alle13:55:22. La verifica successiva associa i processi EngineCore rimasti ai cgroup del K2 ripristinato, non a residui MiMo. Owner/release/health e timestamp distinti sono in `final-live.json`.

PERF-BASELINE-001 resta terminale PARTIAL_ENGINE_DECODE_ONLY. Nessuno dei suoi benchmark è stato ripetuto; i tempi incidentali di questa campagna non lo sostituiscono.

## Un solo passo successivo proposto, non eseguito

Un nuovo pannello holdout preregistrato, più vicino ai flussi reali, concentrato su contratti JSON, citazioni documentali e ottimizzazione vincolata, mantenendo validator deterministici indipendenti e le due configurazioni congelate. Nessun caso di questo lotto viene riscritto o rilanciato.
