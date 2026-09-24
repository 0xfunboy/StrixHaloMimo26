# CURRENT: campagna attiva e checkpoint

**Osservazione:** 2026-09-24T08:35:03.046300+02:00
**Task:** STRIX-GENERALIST-SELECTION-001.
**Fase:** finestra Qwen Q in corso; nessun risultato di selezione finale.

## Preregistrazione e perimetro

Base e6a814336e6f37e88b1cd3a5fab23fc5b299635d. Preparazione locale45c8fd7b6122f050a7593c7ac9d42b1f0c7cd9a2. Indice89 file a47047e2b02e13ef09116c2e11f57ddfd12b8c5617823290f5148a150b5acb98 verificato sui due nodi.12 nuovi casi sintetici, quattro profili reasoning a16K, specOFF, nessun retry semantico. MTP Qwen bloccato dal contratto OFF/ON non esposto, non qualificato.

Root canonica: `/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001/`. Leggere HANDOFF.md, registry.json, PROTOCOL.md e source-manifest.json. [Evidenza della campagna](evidence/results/STRIX_GENERALIST_SELECTION_001_2026-09-24.md).

## Finestra e restore

Run Q: `/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001`. Supervisor mimo26-gs001-supervisor-q-001.service, InvocationID8d0e5c375e9d4518b7da9c21e80333d1; worker mimo26-gs001-q-r0-001, InvocationID9a2835cfa3a34637abcfd2c145c980f1. CaricamentoPASS e controllo tokenizerPASS. La raccolta preliminare e ancora in corso; non duplicare richieste.

K2 e stato sospeso tramite il controller qualificato per questa finestra. Il target di restore salvato e K2 dspark-k2-gfx1151, release5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513, NON E1. Le ricevute admission/k2-before/off ed eventi sono nel run. Il supervisor conserva ExecStopPost e timeout finiti. Non terminare gli EngineCore DS41 dopo il restore: sono residenti legittimi.

## Campagne protette

PERF-BASELINE-001 resta PARTIAL_ENGINE_DECODE_ONLY. QUALITY-RETENTION-001 e QUALITY-HOLDOUT-002 restano concluse e separate. I lotti DS4/HaloPipe terminali non sono riaperti.740 file delle campagne chiuse e44 scratch verificati invariati prima del freeze. Nessun push, deployment, aggiornamento globale o modifica delle release. Snapshot precedente preservato in archive/CURRENT_PRE_GENERALIST_SELECTION_001_2026-09-24.md.

## NEXT EXACT ACTION

Riconciliare il supervisor Q gia avviato, leggere raw/progress/result e attendere il restore verificato senza replay. Poi proseguire soltanto nell ordine autorizzato M→restore→D→restore→O→restore tramite sources/launch.py. Un blocco tecnico richiede causa e isolamento espliciti; niente sostituzioni o tuning. Consegna finale con una sola prossima azione non eseguita.
