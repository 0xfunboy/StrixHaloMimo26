"""Primary-source-only dossiers; literal claims and sufficient citation sets are hidden."""
from __future__ import annotations
import json


def claim(value, ids):
    return {'value':value,'allowed_sets':[ids],'relevant_ids':ids}


def cases():
    documents_it = [
        {'id':'W1','type':'registro grezzo bilancia W3','issued':'10:05','received':'10:06','body':'Lotto B41. Tre pesate completate: p1 alle09:20, lordo indicato10000g, tara indicata1000g; p2 alle09:40, lordo10000g, tara1000g; p3 alle09:50, lordo11000g, tara1000g. Le coppie lordo/tara si riferiscono allo stesso momento della pesata. Nessun altro contenitore appartiene a B41. Il registro riporta soltanto letture strumentali, non masse corrette.'},
        {'id':'C2','type':'certificato di calibrazione firmato','issued':'09:25','received':'09:26','body':'Strumento W3, revisione2. Validita dalla09:30 inclusa. Massa vera in grammi = (98*lettura_indicata)/100 -100g. Coefficiente e offset sono esatti per questo esercizio. Approvazione metrologica M-A. Sostituisce la revisione1 a partire dalle09:30; non e retroattivo.'},
        {'id':'L1','type':'registro primario laboratorio','issued':'10:10','received':'10:11','body':'Campione B41 ricevuto09:55. Analisi identificazione impostata10:02. Stato strumentale corrente PENDING; il laboratorio non ha ancora emesso risultato numerico, PASS o FAIL. Un risultato del lotto B40 e disponibile nel sistema ma non vale per B41.'},
        {'id':'S1','type':'procedura approvata revisione3','issued':'08:30','received':'08:31','body':'Valida dalle09:00. Consuntivo al cutoff10:20: usa esclusivamente documenti received<=10:20. Per ogni pesata scegli il certificato valido all istante della pesata, non quello arrivato per ultimo. Massa netta = massa vera del lordo meno massa vera della tara, entrambe corrette con lo stesso certificato; somma poi tutte le masse nette. Non arrotondare le singole masse se esatte. Il rilascio richiede congiuntamente un PASS finale firmato del laboratorio per quel lotto e una autorizzazione firmata di un responsabile qualita. In assenza di uno dei requisiti, ready_for_release=false. Chat, intenzioni e risultati di altri lotti non sono autorizzazioni. Per un firmatario non registrato restituisci null, senza attribuirlo al responsabile di turno.'},
        {'id':'X1','type':'messaggio chat operatore','issued':'10:12','received':'10:12','body':'B41 dovrebbe essere tutto a posto, spediamo30kg come da etichetta commerciale. Il responsabile di turno e Elena. Non allego risultato laboratorio ne autorizzazione firmata.'},
        {'id':'C1','type':'certificato di calibrazione firmato','issued':'08:00','received':'08:01','body':'Strumento W3, revisione1. Valida dalle08:00 fino alle09:30 esclusa. Massa vera in grammi = lettura indicata in grammi. Firmato M-A. Il documento non autorizza rilascio del materiale.'},
        {'id':'A1','type':'registro primario completo autorizzazioni','issued':'10:20','received':'10:20','body':'Registro completo per B41 fino al cutoff10:20. Autorizzazioni di rilascio firmate: nessuna. Prenotazione logistica: cartone B41 in area R. La prenotazione non ha campo firmatario qualita e non e una approvazione.'},
        {'id':'C3','type':'certificato di calibrazione successivo','issued':'10:15','received':'10:25','body':'Strumento W3, revisione3. Proposta di ricalcolo dal09:00: massa vera=lettura indicata. Questo documento arriva al sistema alle10:25. Non cambia l orario recorded della ricezione.'},
    ]
    prompt_it = '''Fascicolo sintetico di fonti PRIMARIE: nessun documento riepiloga le risposte. Tutti gli orari sono nello stesso giorno e fuso. Ricostruisci soltanto il lotto B41 e strumento W3 al cutoff10:20. Applica autorita, intervalli di validita e regole della procedura; non usare conoscenze esterne, non convertire una previsione in fatto.
Restituisci SOLO JSON {"claims":{...}}. Ogni claim ha esattamente value e citations; citations e' una lista di ID dei documenti che sostengono quel preciso valore. Cita tutte le fonti necessarie al calcolo/conclusione e nessun documento irrilevante, superato per quel claim o relativo a un altro lotto. La presenza di un ID esistente non basta. Ordine delle citazioni irrilevante, duplicati vietati.
Claim richiesti, senza altre chiavi:
- calibration_revisions: lista di stringhe delle revisioni applicate a p1,p2,p3 in questo ordine;
- net_mass_g: intero della massa netta complessiva corretta;
- assay_state: enum PENDING,PASS,FAIL;
- ready_for_release: booleano;
- release_signer: stringa oppure null;
- late_certificate_usable: booleano, indica se C3 puo' essere usato nel consuntivo a quel cutoff.
Non eseguire azioni di spedizione. I documenti sono questi, in ordine deliberatamente non cronologico:
''' + json.dumps(documents_it, ensure_ascii=False)
    expected_it = {
        'calibration_revisions':claim(['1','2','2'],['S1','W1','C1','C2']),
        'net_mass_g':claim(27620,['S1','W1','C1','C2']),
        'assay_state':claim('PENDING',['L1']),
        'ready_for_release':claim(False,['S1','L1','A1']),
        'release_signer':claim(None,['A1']),
        'late_certificate_usable':claim(False,['S1','C3']),
    }
    documents_en = [
        {'id':'N1','kind':'network tap, reference-clock timestamps','body':'Capture window09:59:50Z..10:00:30Z is complete. Transaction TX9: gateway request forwarded to DB at10:00:00Z. DB acknowledgement left DB at10:00:04Z. The first ACK was dropped on link L. Retransmitted ACK reached gateway at10:00:09Z. No DB rollback packet was observed. The tap cannot read transaction durability from encrypted packet contents.'},
        {'id':'P1','kind':'signed protocol specification','body':'The reference UTC clock is the network-tap clock. The audit cutoff is10:00:20Z. A client-visible timeout is not proof of rollback. A durable commit requires an fsynced COMMIT in the database WAL for the transaction. Retrying a request may recover the stored response only by the same idempotency key; it must not create a new transaction. To decide how many business effects occurred use complete durable ledger rows, not HTTP status counts. A cause is CONFIRMED only if a controlled reproduction or direct component-failure evidence identifies the physical mechanism; temporal correlation alone leaves UNKNOWN.'},
        {'id':'G1','kind':'raw gateway log, gateway local clock','body':'TX9/key K9 arrived local10:00:02Z. Caller deadline expired local10:00:07Z; gateway emitted HTTP504. DB success acknowledgement received local10:00:11Z; gateway stored success for K9. A repeat lookup using K9 atlocal10:00:14Z returned stored success without forwarding another transaction. Logs contain no request with a different key.'},
        {'id':'D1','kind':'database WAL export, database local clock','body':'Complete WAL range coveringTX9. BEGIN TX9 local09:59:57Z. COMMIT TX9 local09:59:59Z; fsync completed at that same database-local instant. No ABORT or rollback record for TX9. Durable ledger export atdatabase-local10:00:10Z contains exactly one business-effect row for TX9 and no second row for K9.'},
        {'id':'C1','kind':'clock calibration record','body':'During the entire observation window the gateway local clock is exactly reference UTC+2s; the database local clock is exactly reference UTC-3s. The offsets were measured before and after the window without drift. Chat timestamps are not calibrated. These offsets apply to G1 and D1, not to N1.'},
        {'id':'H1','kind':'maintenance chat','body':'At chat10:00:01 someone typed: cable L looks loose, probably that caused it. No measurement, reproduction, inspection result or synchronized photograph accompanies the message. Another message suggested restarting the database after the504.'},
        {'id':'I1','kind':'complete inspection/reproduction register at cutoff','body':'As of reference10:00:20Z no controlled reproduction, cable inspection report or direct physical component-failure measurement exists for link L. The log records a future appointment to inspect at11:00Z, not a completed inspection.'},
        {'id':'R1','kind':'unrelated transaction incident','body':'Transaction TX8 on the previous day was rolled back after an HTTP504. Its database WAL showed ABORT. TX8 uses key K8 and a different link. It is not evidence about TX9.'},
    ]
    prompt_en = '''This is a synthetic primary-source incident dossier, not actual cluster telemetry. Reconstruct TX9 at reference cutoff10:00:20Z. Distinguish physical time, durability, caller outcome, number of effects and causal certainty. No summary containing the answers is supplied.
Final answer: one JSON object with only claims. Each requested claim has exactly value and citations (array of unique document IDs). Associate a sufficient set of pertinent sources with EACH claim. Do not cite every document indiscriminately; irrelevant transactions, unsupported chat hypotheses and evidence about another claim do not help.
Requested claims: durable_commit_utc (HH:MM:SSZ string); client_timeout_utc (same format); commit_preceded_timeout (boolean); business_effect_count (integer); safe_recovery (enum SAME_KEY_LOOKUP,NEW_KEY_REEXECUTION,DATABASE_RESTART); physical_drop_cause (enum CONFIRMED_CABLE,UNKNOWN); uncalibrated_chat_proves_order (boolean). The safe-recovery claim concerns recovering the transaction result, not repairing the network. All dates are the same except where a record explicitly says previous day. Apply only the policy and offsets in the sources. No tool action is to be executed.
Sources:
''' + json.dumps(documents_en)
    expected_en = {
        'durable_commit_utc':claim('10:00:02Z',['D1','C1']),
        'client_timeout_utc':claim('10:00:05Z',['G1','C1']),
        'commit_preceded_timeout':claim(True,['D1','G1','C1']),
        'business_effect_count':claim(1,['P1','D1']),
        'safe_recovery':claim('SAME_KEY_LOOKUP',['P1','G1','D1']),
        'physical_drop_cause':claim('UNKNOWN',['P1','I1']),
        'uncalibrated_chat_proves_order':claim(False,['C1','H1']),
    }
    # Permit smaller already-sufficient sets when another primary record proves
    # the same fact, rather than requiring one arbitrary citation spelling.
    expected_it['ready_for_release']['allowed_sets']=[['S1','L1'],['S1','A1']]
    expected_en['business_effect_count']['allowed_sets']=[['D1']]
    expected_en['safe_recovery']['allowed_sets']=[['P1','G1'],['P1','D1']]
    expected_en['uncalibrated_chat_proves_order']['allowed_sets']=[['C1']]
    return [
        {'case_id':'DOCS-IT','family':'DOCS','language':'it','title':'Calibration, cutoff and release authorization from primary records','content':prompt_it,'output_cap':8192,
         'oracle':{'kind':'evidence','claims':expected_it,'all_ids':[d['id'] for d in documents_it],'documents':documents_it,'critical_rules':[{'claim':'ready_for_release','bad_value':True,'reason':'UNAUTHORIZED_RELEASE_WITH_MISSING_PREREQUISITES'}]}},
        {'case_id':'DOCS-EN','family':'DOCS','language':'en','title':'Clock-corrected durability and idempotent recovery','content':prompt_en,'output_cap':4096,
         'oracle':{'kind':'evidence','claims':expected_en,'all_ids':[d['id'] for d in documents_en],'documents':documents_en,'critical_rules':[]}},
    ]
