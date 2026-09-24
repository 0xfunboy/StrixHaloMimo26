# M: sanity code_clamp fallito, pannello non ammesso

Run: `generalist-selection-001-M-001`, NODE01. Sanity terminale alle2026-09-24T10:56:15+0200.

Cinque sanity PASS: arithmetic, extract, JSON, italiano, inglese. Il sesto termina naturalmente con57 token di input e75 di output, contro cap1536: non e un incompleto di budget. Il finale nativo contiene:

```python
def clamp(x, lo, hi):
   壓 = x if lo <= x <= hi else (lo if x < lo else hi)
```

La funzione assegna il valore a una variabile locale ma non restituisce il risultato. Tutti e quattro i test del sandbox congelato restituiscono None (`actual:null`), senza eccezioni; quindi FAIL_CODE_TEST e appropriato. La presenza di un ragionamento che descrive correttamente il ternario non corregge il programma finale. Nessuna sostituzione di token, aggiunta di return o nuova generazione viene applicata.

Evidenze:

- `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-M-001/requests/preflight__SANITY-code_clamp/result.json`
- `.../sanity-pre.json`
- `.../fatal.json`, causa `SANITY_PREFLIGHT_FAIL`
- `.../result.json` e ricevute di cleanup/restore della stessa finestra.

Il wrapper conserva l'etichetta generale TECHNICAL_ERROR nel fatal; la causa concreta e invece un errore semantico del sanity di ammissione. Non e una dimostrazione di corruzione del runtime, ne isola l'effetto della quantizzazione o del thinking. La build HIP e i pesi sono quelli fissati; questo e il profilo nuovo ON/temperature1/context16K/seed101, non una riscrittura dei vecchi risultati OFF.

Il gate preregistrato richiede tutti i sanity prima del pannello. Sei richieste sanity sono state registrate; ZERO delle12 richieste del pannello e ZERO dei nuovi benchmark engine sono state inviate. Nei confronti questi12 casi sono NOT_RUN, non dodici errori del modello. Non si ripete il sanity per ottenere PASS e non si allarga il gate dopo il risultato.

Il blocco e ISOLATED_TO_PROFILE M. Dopo il suo restore verificato, D e O possono proseguire con i propri input/configurazioni congelati. Nessuna modifica a codice residente, API, modelli o runtime condivisi e necessaria. Il restore deve essere letto nelle ricevute effettive prima del prossimo avvio; gli EngineCore K2 ripristinati sono residenti legittimi.
