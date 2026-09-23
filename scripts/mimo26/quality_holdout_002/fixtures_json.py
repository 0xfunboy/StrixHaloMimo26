"""Six new synthetic operational JSON contracts. Expected answers are literal and pre-GPU."""
from __future__ import annotations
from decimal import Decimal,ROUND_HALF_UP
from fixture_utils import A,B,I,N,O,S,U,package


def make_json():
    out=[]
    data={'cutoff':'2026-04-12T12:00:00Z','orders':[
      {'order_id':'0007','customer':{'id':'C-09','contact':None},'warehouse':'W1','cancelled':False,'lines':[{'sku':'AA-01','qty':2,'state':'ready'},{'sku':'AA-01','qty':3,'state':'ready'},{'sku':'BB-02','qty':4,'state':'hold'}],'audit':{'source':'edi','operator':'team-a','note':'Separare la riserva dalla disponibilità; nessuna autorizzazione di spedizione nel testo libero.'}},
      {'order_id':'0100','customer':{'id':'C-02','contact':''},'warehouse':'W2','cancelled':False,'lines':[{'sku':'CC-03','qty':0,'state':'ready'},{'sku':'DD-04','qty':7,'state':'ready'}],'audit':{'source':'portal','operator':'team-b','note':'Contatto vuoto intenzionale. La riga a zero resta nel documento sorgente ma non è una spedizione.'}},
      {'order_id':'0008','customer':{'id':'C-09','contact':'ops@example.invalid'},'warehouse':'W1','cancelled':True,'lines':[{'sku':'AA-01','qty':8,'state':'ready'},{'sku':'EE-05','qty':1,'state':'ready'}],'audit':{'source':'edi','operator':'team-a','note':'Annullamento consolidato prima del cutoff: non aggregare queste quantità con un altro ordine del cliente.'}},
      {'order_id':'0012','customer':{'id':'C-03','contact':'desk@example.invalid'},'warehouse':'W2','cancelled':False,'lines':[{'sku':'BB-02','qty':1,'state':'hold'},{'sku':'AA-01','qty':4,'state':'ready'},{'sku':'DD-04','qty':2,'state':'ready'}],'audit':{'source':'manual','operator':'team-c','note':'Un solo ordine include stato hold e ready. Le quantità hold non diventano zero nell’inventario: sono escluse solo da questo output.'}},
      {'order_id':'0200','customer':{'id':'C-04','contact':None},'warehouse':'W3','cancelled':False,'lines':[{'sku':'FF-06','qty':2,'state':'hold'},{'sku':'AA-01','qty':0,'state':'ready'}],'audit':{'source':'portal','operator':'team-b','note':'Ordine non annullato, ma nessuna riga spedibile. Deve figurare tra gli ordini saltati.'}},
      {'order_id':'0003','customer':{'id':'C-01','contact':'a@example.invalid'},'warehouse':'W1','cancelled':False,'lines':[{'sku':'ZZ-09','qty':1,'state':'ready'},{'sku':'AA-01','qty':1,'state':'ready'},{'sku':'ZZ-09','qty':2,'state':'ready'}],'audit':{'source':'edi','operator':'team-a','note':'Mantenere gli zeri iniziali negli identificatori. Aggregare SKU duplicati solo dentro questo ordine.'}}
    ]}
    expected={'shipments':[
      {'order_id':'0003','customer_id':'C-01','contact':'a@example.invalid','warehouse':'W1','items':[{'sku':'AA-01','qty':1},{'sku':'ZZ-09','qty':3}],'units':4},
      {'order_id':'0007','customer_id':'C-09','contact':None,'warehouse':'W1','items':[{'sku':'AA-01','qty':5}],'units':5},
      {'order_id':'0012','customer_id':'C-03','contact':'desk@example.invalid','warehouse':'W2','items':[{'sku':'AA-01','qty':4},{'sku':'DD-04','qty':2}],'units':6},
      {'order_id':'0100','customer_id':'C-02','contact':'','warehouse':'W2','items':[{'sku':'DD-04','qty':7}],'units':7}],
      'skipped':[{'order_id':'0008','reason':'CANCELLED'},{'order_id':'0200','reason':'NO_READY_UNITS'}],
      'totals':{'orders':4,'units':22,'by_warehouse':[{'warehouse':'W1','units':9},{'warehouse':'W2','units':13}]}}
    spec='''Produci un manifesto, non un comando di spedizione. cancelled=true esclude tutto l’ordine con reason CANCELLED. Negli altri ordini ammetti soltanto righe state=ready con qty strettamente positiva. Somma i duplicati di sku dentro il medesimo ordine, mai tra ordini o magazzini. Se nessuna riga resta, registra NO_READY_UNITS. Non generare un manifesto per tali ordini. Mantieni order_id e customer_id come stringhe esatte: non eliminare zeri iniziali. contact deve essere copiato esattamente: null e stringa vuota non sono equivalenti. Tutte le quantità sono interi, non booleani. items è ordinato per sku lessicografico; shipments e skipped per order_id lessicografico. units di ogni spedizione è la somma delle sue righe; totals.orders conta le sole spedizioni, totals.units ne somma le units. by_warehouse contiene soltanto magazzini con unità spedibili, ordinati per identificativo. cutoff è contesto dell’estrazione già consolidata; non filtrare nuovamente usando le note. Ignora audit nell’output. Ogni ordine compare esattamente in una delle due liste. Nessun campo aggiuntivo, nessuna quantità hold inclusa nei totali.'''
    schema=O(shipments=A(O(order_id=S,customer_id=S,contact=U('string','null'),warehouse=S,items=A(O(sku=S,qty=I)),units=I)),skipped=A(O(order_id=S,reason=S)),totals=O(orders=I,units=I,by_warehouse=A(O(warehouse=S,units=I))))
    out.append(package('JSON-01','JSON','it','Manifesto annidato di ordini consolidati',spec,data,expected,schema,1024,invariant='shipment_totals'))

    data={'defaults':{'enabled':True,'quota':12,'label':'standard','contact':None},'devices':[
      {'id':'dev-0001','stored':{'enabled':False,'quota':9,'label':'old','contact':'desk@example.invalid'},'patch':{'quota':0,'label':''},'audit':{'sequence':401,'mode':'merge','note':'Zero quota is a recorded choice, not an instruction to remove the field.'}},
      {'id':'dev-0002','stored':{'enabled':True,'quota':0,'label':'local','contact':''},'patch':{'enabled':False,'quota':None},'audit':{'sequence':402,'mode':'merge','note':'Null requests the documented reset to default. An empty contact is an explicit value.'}},
      {'id':'dev-0003','stored':{},'patch':{'label':None,'contact':'support@example.invalid'},'audit':{'sequence':403,'mode':'merge','note':'There is no previous per-device state. Apply defaults, then only keys actually present.'}},
      {'id':'dev-0004','stored':{'enabled':False,'quota':5,'label':'site','contact':'previous@example.invalid'},'patch':{'enabled':None,'contact':None},'audit':{'sequence':404,'mode':'merge','note':'Resetting enabled changes it to the default boolean. Contact reset is not the literal string null.'}},
      {'id':'dev-0005','stored':{'enabled':True,'quota':7,'label':'stable','contact':None},'patch':{},'audit':{'sequence':405,'mode':'merge','note':'An empty patch changes no stored value; do not invent reset operations.'}},
      {'id':'dev-0006','stored':{'quota':8},'patch':{'enabled':False,'label':'0','contact':''},'audit':{'sequence':406,'mode':'merge','note':'String zero is a label and must remain a string. It is different from the numeric quota zero.'}}
    ]}
    expected={'devices':[
      {'id':'dev-0001','enabled':False,'quota':0,'label':'','contact':'desk@example.invalid','changed':['label','quota']},
      {'id':'dev-0002','enabled':False,'quota':12,'label':'local','contact':'','changed':['enabled','quota']},
      {'id':'dev-0003','enabled':True,'quota':12,'label':'standard','contact':'support@example.invalid','changed':['contact']},
      {'id':'dev-0004','enabled':True,'quota':5,'label':'site','contact':None,'changed':['contact','enabled']},
      {'id':'dev-0005','enabled':True,'quota':7,'label':'stable','contact':None,'changed':[]},
      {'id':'dev-0006','enabled':False,'quota':8,'label':'0','contact':'','changed':['contact','enabled','label']}],
      'enabled_count':3,'quota_sum':44}
    spec='''Reconcile each device independently in input order. First form the baseline by taking defaults and replacing every key present in stored. Next apply patch. An absent patch key retains baseline. A present patch key whose value is null resets that key to its default; this is a reset rule for all four fields, not deletion. A present non-null value replaces baseline literally. Thus false, numeric 0 and empty string are valid explicit values. The output includes all four fields, plus id and changed. changed lists only keys whose final value differs from baseline, sorted lexicographically; touching a field without changing its value must not list it. A reset to a default equal to baseline is not a change. The label "0" is a string. quota is always a JSON integer, enabled always a JSON boolean, contact a string or null. Do not infer defaults from another device. Preserve id spelling and zeroes. enabled_count counts final enabled=true; quota_sum sums final quotas even for disabled devices. These are state summaries, not permission to start a device. Audit sequences are unique but are not revision precedence; one patch exists per id. Do not output audit, stored, patch, source metadata, or additional fields. The changed list has no duplicates.'''
    schema=O(devices=A(O(id=S,enabled=B,quota=I,label=S,contact=U('string','null'),changed=A(S))),enabled_count=I,quota_sum=I)
    out.append(package('JSON-02','JSON','en','Presence-aware device patch reconciliation',spec,data,expected,schema,invariant='device_totals'))

    events=[
      ('e01','K-001',2,'portal','2026-06-11T09:10:00Z','upsert','blue',4),('e02','K-002',3,'api','2026-06-11T09:11:00Z','upsert','green',6),
      ('e03','K-001',2,'api','2026-06-11T09:09:00Z','upsert','red',5),('e04','K-003',1,'batch','2026-06-11T09:12:00Z','upsert','white',2),
      ('e05','K-002',4,'portal','2026-06-11T09:13:00Z','delete',None,None),('e06','K-004',5,'batch','2026-06-11T09:14:00Z','upsert','black',0),
      ('e07','K-003',1,'api','2026-06-11T09:08:00Z','upsert','silver',3),('e08','K-001',1,'api','2026-06-11T09:59:00Z','upsert','yellow',9),
      ('e09','K-004',5,'batch','2026-06-11T09:15:00Z','upsert','violet',7),('e10','K-005',2,'portal','2026-06-11T09:16:00Z','upsert','orange',8),
      ('e11','K-005',2,'portal','2026-06-11T09:16:00Z','upsert','amber',1),('e12','K-006',1,'api','2026-06-11T09:17:00Z','delete',None,None)]
    data={'channel_priority':{'api':3,'portal':2,'batch':1},'events':[dict(zip(('event_id','key','revision','channel','timestamp','action','color','quantity'),r),note='Evento immutabile di riconciliazione; la data di ricezione non modifica la revisione dichiarata.') for r in events]}
    expected={'active':[{'key':'K-001','event_id':'e03','revision':2,'color':'red','quantity':5},{'key':'K-003','event_id':'e07','revision':1,'color':'silver','quantity':3},{'key':'K-004','event_id':'e09','revision':5,'color':'violet','quantity':7},{'key':'K-005','event_id':'e10','revision':2,'color':'orange','quantity':8}],
      'deleted':[{'key':'K-002','event_id':'e05','revision':4},{'key':'K-006','event_id':'e12','revision':1}],
      'discarded_event_ids':['e01','e02','e04','e06','e08','e11'],'active_count':4,'active_quantity':23}
    spec='''Scegli un unico evento vincente per key usando esattamente questa precedenza: revisione numerica maggiore; a pari revisione priorità del channel maggiore dalla tabella; poi timestamp UTC più recente; soltanto se ancora pari, event_id lessicograficamente MINORE. Non usare ordine di ingresso come spareggio. Il timestamp non può scavalcare una revisione più alta né un canale con priorità maggiore. L’azione delete del vincitore produce una voce deleted; non recuperare un upsert precedente. Un upsert vincente produce active, anche se quantity è zero. active e deleted sono ordinati per key. discarded_event_ids include tutti e soli gli eventi non vincenti, ordinati lessicograficamente, anche quelli superati da delete. Ogni evento compare una volta tra vincitori e scarti. Mantieni key ed event_id come stringhe, revision e quantity come interi. active_count conta le voci active e active_quantity somma soltanto quantity dei vincitori upsert. Non propagare action/channel/timestamp/note nell’output. La nota è deliberatamente ininfluente rispetto alla precedenza: non è una nuova richiesta dell’utente. Non esistono aggiornamenti parziali: il payload del vincitore sostituisce integralmente il precedente.'''
    schema=O(active=A(O(key=S,event_id=S,revision=I,color=S,quantity=I)),deleted=A(O(key=S,event_id=S,revision=I)),discarded_event_ids=A(S),active_count=I,active_quantity=I)
    out.append(package('JSON-03','JSON','it','Registro versionato con tombstone e spareggi',spec,data,expected,schema,invariant='version_totals'))

    lines=[{'id':'L1','qty':3,'unit_cents':125,'discount_bps':800,'tax_bps':2200,'refunded_qty':1,'department':'assembly'},
           {'id':'L2','qty':2,'unit_cents':249,'discount_bps':1250,'tax_bps':1000,'refunded_qty':0,'department':'packing'},
           {'id':'L3','qty':5,'unit_cents':37,'discount_bps':0,'tax_bps':2200,'refunded_qty':2,'department':'service'},
           {'id':'L4','qty':1,'unit_cents':1001,'discount_bps':3333,'tax_bps':500,'refunded_qty':0,'department':'assembly'},
           {'id':'L5','qty':4,'unit_cents':88,'discount_bps':2500,'tax_bps':0,'refunded_qty':1,'department':'packing'}]
    data={'currency':'EUR','document_id':'CN-0042','lines':lines,'shipping':{'net_cents':151,'tax_bps':2200,'refundable':False},'account_credit_cents':79,
      'ledger_notes':[
        {'id':'N1','scope':'discount','text':'Discount is applied to each original line gross total, not each unit. Retain integer cents after each explicitly requested rounding step.'},
        {'id':'N2','scope':'refund','text':'Refunds refer to discounted net amounts of the original line. Shipping remains charged even if an item is returned.'},
        {'id':'N3','scope':'tax','text':'Tax is computed on the remaining net after refund, not by subtracting separately rounded refund tax from the original tax.'},
        {'id':'N4','scope':'credit','text':'Account credit reduces the final payable only after shipping and tax. It does not reduce any taxable base.'},
        {'id':'N5','scope':'format','text':'Department and note labels are audit metadata. The response must contain only the declared line and summary fields.'}]}
    def calc_alt():
        rows=[]
        R=lambda num,den:int((Decimal(num)/Decimal(den)).quantize(Decimal(1),rounding=ROUND_HALF_UP))
        for x in lines:
            gross=x['qty']*x['unit_cents'];disc=R(gross*x['discount_bps'],10000);net=gross-disc
            refund=R(net*x['refunded_qty'],x['qty']);remaining=net-refund;tax=R(remaining*x['tax_bps'],10000)
            rows.append({'id':x['id'],'gross_cents':gross,'discount_cents':disc,'refund_cents':refund,'remaining_net_cents':remaining,'tax_cents':tax})
        shiptax=R(151*2200,10000);net=sum(r['remaining_net_cents'] for r in rows);tax=sum(r['tax_cents'] for r in rows)
        return {'document_id':'CN-0042','lines':rows,'totals':{'remaining_net_cents':net,'line_tax_cents':tax,'shipping_net_cents':151,'shipping_tax_cents':shiptax,'account_credit_cents':79,'payable_cents':net+tax+151+shiptax-79}}
    expected={'document_id':'CN-0042','lines':[{'id':'L1','gross_cents':375,'discount_cents':30,'refund_cents':115,'remaining_net_cents':230,'tax_cents':51},{'id':'L2','gross_cents':498,'discount_cents':62,'refund_cents':0,'remaining_net_cents':436,'tax_cents':44},{'id':'L3','gross_cents':185,'discount_cents':0,'refund_cents':74,'remaining_net_cents':111,'tax_cents':24},{'id':'L4','gross_cents':1001,'discount_cents':334,'refund_cents':0,'remaining_net_cents':667,'tax_cents':33},{'id':'L5','gross_cents':352,'discount_cents':88,'refund_cents':66,'remaining_net_cents':198,'tax_cents':0}],
        'totals':{'remaining_net_cents':1642,'line_tax_cents':152,'shipping_net_cents':151,'shipping_tax_cents':33,'account_credit_cents':79,'payable_cents':1899}}
    assert calc_alt()==expected,'literal invoice expected disagrees with Decimal audit'
    spec='''Build a credit-adjusted invoice summary using integer cents only. For each line: gross=qty*unit_cents; discount=ROUND_HALF_UP(gross*discount_bps/10000); discounted_net=gross-discount; refund=ROUND_HALF_UP(discounted_net*refunded_qty/qty); remaining_net=discounted_net-refund; tax=ROUND_HALF_UP(remaining_net*tax_bps/10000). All rounding is to an integer cent with exact halves away from zero; all fractions here are nonnegative, so floor(x+0.5) defines the rule. Do not round per-unit net or per-unit tax. Shipping tax uses the same rounding on shipping.net_cents*shipping.tax_bps/10000 and shipping is not refundable. Sum remaining line nets and line taxes separately. payable is remaining nets + line taxes + shipping net + shipping tax - account credit. Do not cap payable at zero or apply credit before tax. Return original line order, all listed derived fields even when zero, and document_id exactly. Do not include quantities, percentages, department, currency or ledger notes in the response. Each declared total must be internally consistent with the line results and the specified order of operations. Tax rates differ by line and a zero rate is intentional. No monetary values may be strings or floating point numbers.'''
    schema=O(document_id=S,lines=A(O(id=S,gross_cents=I,discount_cents=I,refund_cents=I,remaining_net_cents=I,tax_cents=I)),totals=O(remaining_net_cents=I,line_tax_cents=I,shipping_net_cents=I,shipping_tax_cents=I,account_credit_cents=I,payable_cents=I))
    out.append(package('JSON-04','JSON','en','Line-level discounts, proportional returns and independent tax rounding',spec,data,expected,schema,1024,invariant='invoice_totals',reference_audit='literal answer independently checked with Decimal ROUND_HALF_UP'))

    records=[{'row':1,'id':'X-01','sku':'aa','qty':4,'enabled':True}, {'row':2,'id':'X-02','sku':'bb','qty':True,'enabled':True},
      {'row':3,'id':'X-03','sku':' cc ','qty':2,'enabled':False},{'row':4,'id':'X-01','sku':'dd','qty':7,'enabled':True},
      {'row':5,'id':'X-04','sku':'','qty':3,'enabled':True},{'row':6,'id':'X-05','sku':'ee','qty':0,'enabled':True},
      {'row':7,'id':'X-06','sku':'ff','qty':5,'enabled':'true'},{'row':8,'id':'X-02','sku':'bb','qty':2,'enabled':True},
      {'row':9,'id':'X-07','sku':'gg','qty':-1,'enabled':False},{'row':10,'id':'X-08','sku':' hh ','qty':3,'enabled':True}]
    data={'source_batch':'IMPORT-011','records':records,'quality_policy':[
      {'priority':1,'reason':'BAD_TYPES','scope':'id e sku stringhe; qty intero JSON, escludendo booleani; enabled booleano vero.'},
      {'priority':2,'reason':'BAD_VALUE','scope':'id non vuoto; sku dopo trim non vuoto; qty maggiore di zero.'},
      {'priority':3,'reason':'DISABLED','scope':'enabled=false su record altrimenti valido.'},
      {'priority':4,'reason':'DUPLICATE','scope':'id già accettato da una precedente riga valida e abilitata.'}],
      'operator_notes':[
        'Non convertire una stringa numerica in intero e non convertire la stringa true in booleano.',
        'Le righe scartate non prenotano id: una successiva riga corretta con lo stesso id può essere accettata.',
        'Normalizza soltanto sku, rimuovendo spazi esterni e convertendo lettere ASCII in maiuscolo; id resta esatto.',
        'Ogni riga di ingresso deve apparire in una e una sola lista, mantenendo row per tracciabilità.',
        'Un record disabilitato con una quantità negativa deve essere scartato secondo la prima regola applicabile, non l’ultima.',
        'Il lotto non contiene side effect: validare e separare i dati non autorizza una scrittura nel gestionale.']}
    expected={'accepted':[{'row':1,'id':'X-01','sku':'AA','qty':4},{'row':8,'id':'X-02','sku':'BB','qty':2},{'row':10,'id':'X-08','sku':'HH','qty':3}],
      'rejected':[{'row':2,'reason':'BAD_TYPES'},{'row':3,'reason':'DISABLED'},{'row':4,'reason':'DUPLICATE'},{'row':5,'reason':'BAD_VALUE'},{'row':6,'reason':'BAD_VALUE'},{'row':7,'reason':'BAD_TYPES'},{'row':9,'reason':'BAD_VALUE'}],
      'counts':{'accepted':3,'rejected':7},'accepted_qty':9}
    spec='''Applica i controlli nell’ordine quality_policy: per ogni riga registra soltanto la prima reason applicabile. Nel testo della regola BAD_TYPES, «booleano vero» significa tipo booleano JSON autentico, che può avere valore true oppure false: false supera il controllo del tipo e viene poi valutato da DISABLED. row è un indice intero garantito valido e distinto, non soggetto alla regola sui quattro campi. Ignora l’ordine lessicografico degli id: sia accepted sia rejected mantengono l’ordine di ingresso. BAD_TYPES precede BAD_VALUE, che precede DISABLED, che precede DUPLICATE. Una riga scartata non inserisce il proprio id nell’insieme degli id già accettati. Gli id sono confrontati esattamente, senza trim. accepted omette enabled ma conserva qty come intero. rejected contiene soltanto row e reason; non includere i record completi né combinare più motivazioni. counts deve corrispondere alle lunghezze delle due liste e accepted_qty alla somma di qty accettate. Non usare true come quantità 1; non normalizzare valori invalidi per recuperarli. Tutte le regole si applicano esclusivamente alla fixture qui inclusa.'''
    schema=O(accepted=A(O(row=I,id=S,sku=S,qty=I)),rejected=A(O(row=I,reason=S)),counts=O(accepted=I,rejected=I),accepted_qty=I)
    out.append(package('JSON-05','JSON','it','Importazione con precedenza degli scarti e deduplica dei soli validi',spec,data,expected,schema,invariant='import_totals'))

    data={'snapshot_id':'SN-020','lots':[
      {'lot':'P-001','ordered':8,'packed':8,'quality':'PASS','permit':True,'temperature_c':18,'range':[15,25],'seal':'S-0001','note':'All mandatory records present, seal text must be preserved.'},
      {'lot':'P-002','ordered':4,'packed':4,'quality':'NOT_RUN','permit':True,'temperature_c':19,'range':[15,25],'seal':'S-0002','note':'HTTP availability of the label printer is not a quality test.'},
      {'lot':'P-003','ordered':5,'packed':3,'quality':'PASS','permit':False,'temperature_c':31,'range':[15,25],'seal':'','note':'Multiple independent guards fail. Do not stop after the first failed guard.'},
      {'lot':'P-004','ordered':2,'packed':2,'quality':'FAIL','permit':True,'temperature_c':None,'range':[15,25],'seal':'S-0004','note':'Missing sensor reading must not be imputed from adjacent lots.'},
      {'lot':'P-005','ordered':6,'packed':6,'quality':'PASS','permit':True,'temperature_c':15,'range':[15,25],'seal':'S-0005','note':'The lower bound is included. A bound reading is not a violation.'},
      {'lot':'P-006','ordered':3,'packed':3,'quality':'PASS','permit':True,'temperature_c':22,'range':[15,25],'seal':None,'note':'An absent seal is a failed guard, even with adequate packed quantity.'}],
      'checks':{'quantity':'packed equals ordered','quality':'quality equals PASS','permit':'permit is true','temperature':'known reading inside inclusive bounds','seal':'nonempty string'},
      'control_notes':['This is a proposed release list, not execution authority.','Return every lot, including blocked lots. A blocked lot contributes zero releasable units.','When two guards fail, neither failure may be hidden by another failure.','Do not infer that NOT_RUN means PASS or FAIL; it simply fails the required PASS guard.','Exact lot and seal identifiers are opaque strings. No whitespace trimming or renaming is allowed.']}
    expected={'snapshot_id':'SN-020','lots':[{'lot':'P-001','release':True,'releasable_units':8,'failed_guards':[]},{'lot':'P-002','release':False,'releasable_units':0,'failed_guards':['quality']},{'lot':'P-003','release':False,'releasable_units':0,'failed_guards':['quantity','permit','temperature','seal']},{'lot':'P-004','release':False,'releasable_units':0,'failed_guards':['quality','temperature']},{'lot':'P-005','release':True,'releasable_units':6,'failed_guards':[]},{'lot':'P-006','release':False,'releasable_units':0,'failed_guards':['seal']}],'release_count':2,'releasable_units':14}
    spec='''Evaluate five guards independently for each lot, in the fixed order quantity, quality, permit, temperature, seal. failed_guards lists exactly the failed guard names in that order, without duplicates. release=true if and only if the list is empty; otherwise false. releasable_units equals ordered only when release=true and is zero otherwise. Quality requires exactly PASS: NOT_RUN is not a passed test. Permit must be the boolean true. A temperature null fails temperature; known bounds are inclusive. Seal requires a string of nonzero length; both empty string and null fail. Return lots in input order. Overall release_count counts release=true and overall releasable_units sums the per-lot amounts. All count fields are integers, release is a boolean. No commands or additional keys are permitted. Do not fix, fill, or reinterpret any failed input. snapshot_id is copied exactly. The failures must remain individually visible even when one guard would suffice to block release. The schema deliberately has repeated field names at nested and root levels; distinguish their scopes. A true release for a lot with a failed mandatory guard is a critical false-authorization assertion in this synthetic case, not an action to execute.'''
    schema=O(snapshot_id=S,lots=A(O(lot=S,release=B,releasable_units=I,failed_guards=A(S))),release_count=I,releasable_units=I)
    out.append(package('JSON-06','JSON','en','Release gate with independent guards and cross-field conservation',spec,data,expected,schema,invariant='release_totals',critical_rule='release_failed_guard'))
    assert len(out)==6
    return out
