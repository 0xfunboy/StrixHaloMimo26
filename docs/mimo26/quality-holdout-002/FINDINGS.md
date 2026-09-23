# Decisioni e diagnostiche — QUALITY-HOLDOUT-002



### JSON-01 — Manifesto annidato di ordini consolidati

**A: FAIL_SEMANTIC**. $.shipments[0].contact: atteso "a@example.invalid", ricevuto null $.shipments[0].customer_id: atteso "C-01", ricevuto "C-09" $.shipments[0].items: atteso 2, ricevuto 1 $.shipments[0].items[0].qty: atteso 1, ricevuto 5 $.shipments[0].order_id: atteso "0003", ricevuto "0007" $.shipments[0].units: atteso 4, ricevuto 5 $.shipments[1].contact: atteso null, ricevuto "" $.shipments[1].customer_id: atteso "C-09", ricevuto "C-02" $.shipments[1].items[0].qty: atteso 5, ricevuto 7 $.shipments[1].items[0].sku: atteso "AA-01", ricevuto "DD-04" $.shipments[1].order_id: atteso "0007", ricevuto "0100" $.shipments[1].units: atteso 5, ricevuto 7 $.shipments[1].warehouse: atteso "W1", ricevuto "W2" $.shipments[3].contact: atteso "", ricevuto "a@example.invalid" $.shipments[3].customer_id: atteso "C-02", ricevuto "C-01" $.shipments[3].items: atteso 1, ricevuto 2 $.shipments[3].items[0].qty: atteso 7, ricevuto 1 $.shipments[3].items[0].sku: atteso "DD-04", ricevuto "AA-01" $.shipments[3].order_id: atteso "0100", ricevuto "0003" $.shipments[3].units: atteso 7, ricevuto 4 $.shipments[3].warehouse: atteso "W2", ricevuto "W1"
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__JSON-01/result.json`.
**B: PASS**. Nessun errore osservato nel caso.
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__JSON-01/result.json`.

### JSON-02 — Presence-aware device patch reconciliation

**A: FAIL_SEMANTIC**. $.devices[0].enabled: atteso false, ricevuto true $.devices[5].changed[0]: atteso "contact", ricevuto "enabled" $.devices[5].changed[1]: atteso "enabled", ricevuto "label" $.devices[5].changed[2]: atteso "label", ricevuto "contact"
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__JSON-02/result.json`.
**B: FAIL_SEMANTIC**. $.enabled_count: atteso 3, ricevuto 2
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__JSON-02/result.json`.

### JSON-03 — Registro versionato con tombstone e spareggi

**A: FAIL_SEMANTIC**. $.active[2].color: atteso "violet", ricevuto "black" $.active[2].event_id: atteso "e09", ricevuto "e06" $.active[2].quantity: atteso 7, ricevuto 0 $.active_quantity: atteso 23, ricevuto 16 $.discarded_event_ids[3]: atteso "e06", ricevuto "e08" $.discarded_event_ids[4]: atteso "e08", ricevuto "e09"
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__JSON-03/result.json`.
**B: FAIL_SEMANTIC**. $.active[2].color: atteso "violet", ricevuto "black" $.active[2].event_id: atteso "e09", ricevuto "e06" $.active[2].quantity: atteso 7, ricevuto 0 $.active[3].color: atteso "orange", ricevuto "amber" $.active[3].event_id: atteso "e10", ricevuto "e11" $.active[3].quantity: atteso 8, ricevuto 1 $.active_quantity: atteso 23, ricevuto 9 $.discarded_event_ids[3]: atteso "e06", ricevuto "e08" $.discarded_event_ids[4]: atteso "e08", ricevuto "e09" $.discarded_event_ids[5]: atteso "e11", ricevuto "e10"
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__JSON-03/result.json`.

### JSON-04 — Line-level discounts, proportional returns and independent tax rounding

**A: FAIL_SEMANTIC**. $.lines[4].refund_cents: atteso 66, ricevuto 198 $.lines[4].remaining_net_cents: atteso 198, ricevuto 166 $.totals.payable_cents: atteso 1899, ricevuto 1867 $.totals.remaining_net_cents: atteso 1642, ricevuto 1610
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__JSON-04/result.json`.
**B: PASS**. Nessun errore osservato nel caso.
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__JSON-04/result.json`.

### JSON-05 — Importazione con precedenza degli scarti e deduplica dei soli validi

**A: FAIL_SEMANTIC**. $.accepted: atteso 3, ricevuto 6 $.accepted[1].id: atteso "X-02", ricevuto "X-03" $.accepted[1].row: atteso 8, ricevuto 3 $.accepted[1].sku: atteso "BB", ricevuto "CC" $.accepted[2].id: atteso "X-08", ricevuto "X-01" $.accepted[2].qty: atteso 3, ricevuto 7 $.accepted[2].row: atteso 10, ricevuto 4 $.accepted[2].sku: atteso "HH", ricevuto "DD" $.accepted_qty: atteso 9, ricevuto 18 $.counts.accepted: atteso 3, ricevuto 6 $.counts.rejected: atteso 7, ricevuto 4 $.rejected: atteso 7, ricevuto 4 $.rejected[1].reason: atteso "DISABLED", ricevuto "BAD_VALUE" $.rejected[1].row: atteso 3, ricevuto 5 $.rejected[2].reason: atteso "DUPLICATE", ricevuto "BAD_TYPES" $.rejected[2].row: atteso 4, ricevuto 7 $.rejected[3].row: atteso 5, ricevuto 9
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__JSON-05/result.json`.
**B: FAIL_SEMANTIC**. $.accepted: atteso 3, ricevuto 4 $.accepted[1].id: atteso "X-02", ricevuto "X-03" $.accepted[1].row: atteso 8, ricevuto 3 $.accepted[1].sku: atteso "BB", ricevuto "CC" $.accepted[2].id: atteso "X-08", ricevuto "X-05" $.accepted[2].qty: atteso 3, ricevuto 0 $.accepted[2].row: atteso 10, ricevuto 6 $.accepted[2].sku: atteso "HH", ricevuto "EE" $.counts.accepted: atteso 3, ricevuto 4 $.counts.rejected: atteso 7, ricevuto 6 $.rejected: atteso 7, ricevuto 6 $.rejected[1].reason: atteso "DISABLED", ricevuto "DUPLICATE" $.rejected[1].row: atteso 3, ricevuto 4 $.rejected[2].reason: atteso "DUPLICATE", ricevuto "BAD_VALUE" $.rejected[2].row: atteso 4, ricevuto 5 $.rejected[3].reason: atteso "BAD_VALUE", ricevuto "BAD_TYPES" $.rejected[3].row: atteso 5, ricevuto 7 $.rejected[4].reason: atteso "BAD_VALUE", ricevuto "DUPLICATE" $.rejected[4].row: atteso 6, ricevuto 8 $.rejected[5].reason: atteso "BAD_TYPES", ricevuto "BAD_VALUE" $.rejected[5].row: atteso 7, ricevuto 9
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__JSON-05/result.json`.

### CONSTRAINT-02 — Coverage-constrained two-zone pipeline selection

**A: FAIL_SEMANTIC**. cost 13 > budget 12 missing coverage format-B cost: dichiarato 11, ricalcolato 13 ottimalità primaria non soddisfatta ricalcolo indipendente: {"cost": 13, "ids": ["N2", "O1", "P1", "S1"], "risk": 3, "status": "OPTIMAL", "value": 27}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__CONSTRAINT-02/result.json`.
**B: PASS**. Nessun errore osservato nel caso.
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__CONSTRAINT-02/result.json`.

### CONSTRAINT-03 — Percorso con checkpoint ordinati e priorità costo-rischio-tempo

**A: FAIL_SEMANTIC**. cost: dichiarato 7, ricalcolato 9 time: dichiarato 8, ricalcolato 11 tie-break non soddisfatto ricalcolo indipendente: {"cost": 9, "path": ["S", "B", "P", "D", "Q", "T"], "risk": 1, "status": "OPTIMAL", "time": 11}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__CONSTRAINT-03/result.json`.
**B: FAIL_SEMANTIC**. cost: dichiarato 8, ricalcolato 9 risk: dichiarato 1, ricalcolato 2 tie-break non soddisfatto ricalcolo indipendente: {"cost": 9, "path": ["S", "B", "P", "C", "Q", "T"], "risk": 2, "status": "OPTIMAL", "time": 9}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__CONSTRAINT-03/result.json`.

### CONSTRAINT-04 — Risk-first route with a forbidden vertex and ordered coverage

**A: FAIL_SEMANTIC**. cost: dichiarato 7, ricalcolato 9 time: dichiarato 8, ricalcolato 10 ottimalità primaria non soddisfatta ricalcolo indipendente: {"cost": 9, "path": ["U", "H", "K", "M", "Z"], "risk": 1, "status": "OPTIMAL", "time": 10}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__CONSTRAINT-04/result.json`.
**B: FAIL_SEMANTIC**. cost: dichiarato 11, ricalcolato 10 risk: dichiarato 1, ricalcolato 0 time: dichiarato 12, ricalcolato 11 ricalcolo indipendente: {"cost": 10, "path": ["U", "H", "K", "N", "M", "Z"], "risk": 0, "status": "OPTIMAL", "time": 11}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__CONSTRAINT-04/result.json`.

### CONSTRAINT-05 — Assegnazione con competenze, precedenze, risorsa esclusiva e tie-break

**A: FAIL_SEMANTIC**. double booking W-A slot 2 cost: dichiarato 10, ricalcolato 11 ottimalità primaria non soddisfatta ricalcolo indipendente: {"assignments": [{"job": "J1", "slot": 0, "worker": "W-A"}, {"job": "J2", "slot": 0, "worker": "W-B"}, {"job": "J3", "slot": 1, "worker": "W-B"}, {"job": "J4", "slot": 2, "worker": "W-A"}, {"job": "J5", "slot": 2, "worker": "W-A"}], "cost": 11, "makespan": 3, "status": "OPTIMAL"}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-A-mixed-001/requests/panel__CONSTRAINT-05/result.json`.
**B: FAIL_SEMANTIC**. J3/J4: same slot forbidden cost: dichiarato 10, ricalcolato 11 ottimalità primaria non soddisfatta ricalcolo indipendente: {"assignments": [{"job": "J1", "slot": 0, "worker": "W-A"}, {"job": "J2", "slot": 0, "worker": "W-B"}, {"job": "J3", "slot": 1, "worker": "W-B"}, {"job": "J4", "slot": 1, "worker": "W-A"}, {"job": "J5", "slot": 2, "worker": "W-A"}], "cost": 11, "makespan": 3, "status": "OPTIMAL"}
Fonte: `/home/funboy/.local/state/strixhalomimo26/windows/quality-holdout-002-B-original-001/requests/panel__CONSTRAINT-05/result.json`.

## Decisione per famiglia, senza esecuzione di pilot

### JSON

A: **CONTAIN_OBSERVED_ERRORS_BEFORE_FAMILY_PILOT**. Casi riusciti: ["JSON-06"]. Errori da contenere: ["JSON-01", "JSON-02", "JSON-03", "JSON-04", "JSON-05"]. Altri stati: [].
B: **CONTAIN_OBSERVED_ERRORS_BEFORE_FAMILY_PILOT**. Casi riusciti: ["JSON-01", "JSON-04", "JSON-06"]. Errori da contenere: ["JSON-02", "JSON-03", "JSON-05"]. Altri stati: [].
Controlli eseguibili sui dati reali: strict parsing, duplicate/nonfinite rejection, schema and exact types; field invariants and recomputation from available input data.
Componenti dedicati ancora necessari, non implementati in produzione: task-specific semantic transformation checks without benchmark expected answers.
A validator can reject malformed or inconsistent data; it does not create the correct missing answer.
Only six targeted synthetic cases in this family. No autonomous use, production deployment, model equivalence or automatic next experiment.

### EVIDENCE

A: **SCOPED_SUPERVISED_PILOT_PROPOSAL_ONLY**. Casi riusciti: ["EVIDENCE-01", "EVIDENCE-02", "EVIDENCE-03", "EVIDENCE-04", "EVIDENCE-05", "EVIDENCE-06"]. Errori da contenere: []. Altri stati: [].
B: **SCOPED_SUPERVISED_PILOT_PROPOSAL_ONLY**. Casi riusciti: ["EVIDENCE-01", "EVIDENCE-02", "EVIDENCE-03", "EVIDENCE-04", "EVIDENCE-05", "EVIDENCE-06"]. Errori da contenere: []. Altri stati: [].
Controlli eseguibili sui dati reali: citation-ID existence, per-claim citation presence, record-scope and cutoff metadata checks.
Componenti dedicati ancora necessari, non implementati in produzione: semantic relevance, sufficient evidence coverage and contradictory-source resolution on unseen documents.
Expected claim values and sufficient citation sets are benchmark oracles, not an existing production evidence judge.
Only six targeted synthetic cases in this family. No autonomous use, production deployment, model equivalence or automatic next experiment.

### CONSTRAINT

A: **CONTAIN_OBSERVED_ERRORS_BEFORE_FAMILY_PILOT**. Casi riusciti: ["CONSTRAINT-01", "CONSTRAINT-06"]. Errori da contenere: ["CONSTRAINT-02", "CONSTRAINT-03", "CONSTRAINT-04", "CONSTRAINT-05"]. Altri stati: [].
B: **CONTAIN_OBSERVED_ERRORS_BEFORE_FAMILY_PILOT**. Casi riusciti: ["CONSTRAINT-01", "CONSTRAINT-02", "CONSTRAINT-06"]. Errori da contenere: ["CONSTRAINT-03", "CONSTRAINT-04", "CONSTRAINT-05"]. Altri stati: [].
Controlli eseguibili sui dati reali: feasibility and declared totals recalculated from the proposed plan and input constraints.
Componenti dedicati ancora necessari, non implementati in produzione: separate exact optimizer or optimality certificate for real problem sizes and tie-break rules.
A feasibility checker rejects invalid choices; replacing a solution with a solver answer would be a different treatment.
Only six targeted synthetic cases in this family. No autonomous use, production deployment, model equivalence or automatic next experiment.

