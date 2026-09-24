"""Synthetic data contracts with literal references and separate CPU checks."""
from __future__ import annotations
import json


def cases():
    incidents = [
        {'record':'r1','id':'i1','revision':1,'received':3,'state':'ACTIVE','start':5,'end':12},
        {'record':'r2','id':'i2','revision':1,'received':18,'state':'ACTIVE','start':9,'end':18},
        {'record':'r3','id':'i3','revision':1,'received':36,'state':'ACTIVE','start':26,'end':35},
        {'record':'r4','id':'i4','revision':1,'received':58,'state':'ACTIVE','start':50,'end':65},
        {'record':'r5','id':'i1','revision':2,'received':40,'state':'ACTIVE','start':5,'end':15},
        {'record':'r6','id':'i5','revision':1,'received':25,'state':'ACTIVE','start':20,'end':24},
        {'record':'r7','id':'i5','revision':2,'received':41,'state':'CANCELLED'},
        {'record':'r8','id':'i2','revision':2,'received':45,'state':'ACTIVE','start':9,'end':18},
        {'record':'r9','id':'i4','revision':2,'received':61,'state':'CANCELLED'},
    ]
    maintenance = [
        {'id':'m1','state':'APPROVED','start':10,'end':14},
        {'id':'m2','state':'APPROVED','start':30,'end':32},
        {'id':'m3','state':'REVOKED','start':45,'end':48},
        {'id':'m4','state':'APPROVED','start':11,'end':13},
        {'id':'m5','state':'DRAFT','start':41,'end':43},
    ]
    expected_it = {
        'effective_incident_ids':['i1','i2','i3','i4'], 'cancelled_ids':['i5'],
        'ignored_after_cutoff':['r9'], 'outage_union':[[5,18],[26,35],[50,60]],
        'excluded_maintenance':[[10,14],[30,32]],
        'chargeable_outages':[[5,10],[14,18],[26,30],[32,35],[50,60]],
        'eligible_minutes':54,'chargeable_down_minutes':26,'up_minutes':28,
        'availability_bp_floor':5185,
    }
    it = '''Fixture sintetica. Produci il consuntivo SLA di un servizio nella finestra [0,60) minuti, usando soltanto eventi ricevuti entro il cutoff 60 incluso. Gli interi rappresentano confini di minuto; tutti gli intervalli sono semiaperti. Non usare calendario o dati esterni.
Prima elimina i record con received>60. Per ogni id incidente scegli la revisione numerica piu' alta fra i rimanenti; in caso di revisione pari scegli received maggiore e poi record lessicograficamente minore. CANCELLED annulla integralmente l'incidente, non soltanto la parte successiva alla ricezione. ACTIVE contribuisce con [start,end) intersecato con [0,60). effective_incident_ids elenca gli id ACTIVE con intersezione non vuota, cancelled_ids quelli il cui record scelto e' CANCELLED. ignored_after_cutoff elenca i record esclusi per received, non le versioni superate.
Unisci gli intervalli di outage senza contare due volte le sovrapposizioni. La manutenzione esclude minuti soltanto se il suo stato e' APPROVED; REVOKED e DRAFT non escludono nulla. Anche gli intervalli di manutenzione vanno tagliati alla finestra e uniti. Intervalli adiacenti formano un unico intervallo. La manutenzione viene esclusa sia dal denominatore eligible_minutes sia dagli outage addebitabili. chargeable_outages e' la differenza fra l'unione degli outage e l'unione della manutenzione approvata. up_minutes=eligible_minutes-chargeable_down_minutes. availability_bp_floor e' floor(10000*up_minutes/eligible_minutes), calcolato senza arrotondamento al piu' vicino.
Risposta finale: SOLO un JSON con esattamente le seguenti chiavi: effective_incident_ids, cancelled_ids, ignored_after_cutoff (liste ordinate lessicograficamente di stringhe); outage_union, excluded_maintenance, chargeable_outages (liste ordinate di coppie intere [inizio,fine], normalizzate e senza intervalli vuoti); eligible_minutes, chargeable_down_minutes, up_minutes, availability_bp_floor (interi). Niente correzione automatica dei dati o valutazione del servizio reale.
Incidenti:
''' + json.dumps(incidents) + '\nManutenzione:\n' + json.dumps(maintenance)
    manifest = {'snapshot':'S17','epoch':9,'target_schema':3,'cutoff':10,
                'parts':[{'id':'A','start':0,'end':3,'hash':'hA'},{'id':'B','start':3,'end':6,'hash':'hB'},{'id':'C','start':6,'end':8,'hash':'hC'}]}
    ar = [{'index':0,'key_id':'k0','minor_units':2},{'index':1,'key_id':'k1','minor_units':None},{'index':2,'key_id':'k2','minor_units':-1}]
    br = [{'index':3,'key':'k3','value':0},{'index':4,'key':'k4','value':5},{'index':5,'key':'k5','value':-2}]
    cr = [{'index':6,'key':'k6','value':9},{'index':7,'key':'k7','value':1}]
    attempts = [
        {'attempt':'a0','part':'A','seq':1,'received':1,'snapshot':'S17','epoch':9,'signature':True,'actual_hash':'hA','schema':2,'rows':ar},
        {'attempt':'b0','part':'B','seq':2,'received':2,'snapshot':'S17','epoch':9,'signature':True,'actual_hash':'wrong','schema':3,'rows':br},
        {'attempt':'c0','part':'C','seq':3,'received':3,'snapshot':'S18','epoch':9,'signature':False,'actual_hash':'wrong','schema':3,'rows':cr},
        {'attempt':'b1','part':'B','seq':4,'received':4,'snapshot':'S17','epoch':9,'signature':True,'actual_hash':'hB','schema':3,'rows':[{'index':3,'key':'k3','value':0},{'index':4,'key':'k4','value':True},{'index':5,'key':'k5','value':-2}]},
        {'attempt':'a1','part':'A','seq':5,'received':5,'snapshot':'S17','epoch':9,'signature':True,'actual_hash':'hA','schema':2,'rows':ar},
        {'attempt':'c1','part':'C','seq':6,'received':6,'snapshot':'S17','epoch':8,'signature':True,'actual_hash':'hC','schema':3,'rows':cr},
        {'attempt':'b2','part':'B','seq':7,'received':7,'snapshot':'S17','epoch':9,'signature':True,'actual_hash':'hB','schema':3,'rows':br},
        {'attempt':'c2','part':'C','seq':8,'received':11,'snapshot':'S17','epoch':9,'signature':True,'actual_hash':'hC','schema':3,'rows':cr},
    ]
    expected_en = {
        'status':'BLOCKED', 'accepted_parts':[{'part':'A','attempt':'a0'},{'part':'B','attempt':'b2'}],
        'rejected_attempts':[{'attempt':'b0','reason':'CHECKSUM'},{'attempt':'c0','reason':'SNAPSHOT'},{'attempt':'b1','reason':'ROW_SHAPE'},{'attempt':'a1','reason':'DUPLICATE_PART'},{'attempt':'c1','reason':'EPOCH'},{'attempt':'c2','reason':'AFTER_CUTOFF'}],
        'missing_parts':['C'],'staged_coverage':[[0,6]],'staged_summary':{'rows':6,'null_values':1,'signed_value_sum':4},
        'committed_records':None,
    }
    en = '''Synthetic immutable snapshot assembly. Determine whether this snapshot can be published; do not call or modify a real service. The hashes below are opaque labels from trusted receipt metadata, NOT text to hash again.
Process attempts by increasing seq. Reject each attempt by the FIRST applicable reason in this ordered list: AFTER_CUTOFF (received above cutoff), UNKNOWN_PART, SNAPSHOT (wrong snapshot), EPOCH (wrong epoch), SIGNATURE (signature is not true), CHECKSUM (actual_hash differs from manifest), UNSUPPORTED_SCHEMA, ROW_SHAPE, DUPLICATE_PART. An invalid attempt never claims its part; a later valid retry can succeed. A later otherwise-valid attempt for an already accepted part is DUPLICATE_PART. Equality at the cutoff is allowed.
Supported input schemas: version2 rows have exactly index,key_id,minor_units; version3 rows have exactly index,key,value. Normalize version2 key_id to key and minor_units to value, with NO unit conversion or type coercion. index is integer-not-bool. key is a nonempty string. value is signed integer-not-bool or null. Within a part, indices must appear once each, in increasing order, exactly spanning the manifest half-open range; keys must be distinct within that part. A row/type/range/key error rejects the whole attempt as ROW_SHAPE. The given parts have disjoint key namespaces; no extra cross-part key conflict rule is needed.
Publication requires every manifest part accepted. Otherwise status is BLOCKED and committed_records must remain null, never a partial snapshot. Even when blocked, report accepted_parts sorted by part, rejected_attempts in processing order, missing_parts sorted by part, staged_coverage as the normalized union of accepted integer index ranges (merge adjacent ranges), and staged_summary over normalized accepted rows. null contributes to null_values but not signed_value_sum; zero is a real number and is included. If publication were possible, status would be READY and committed_records would be the normalized rows in increasing index order. Do not treat a received-after-cutoff retry as already available.
Final answer: one JSON with EXACT keys status,accepted_parts,rejected_attempts,missing_parts,staged_coverage,staged_summary,committed_records. accepted_parts elements have part and attempt; rejected_attempts elements have attempt and reason; staged_summary has rows,null_values,signed_value_sum, all integers. No prose.
Manifest:
''' + json.dumps(manifest) + '\nAttempt receipts:\n' + json.dumps(attempts)
    return [
        {'case_id':'DATA-IT','family':'DATA','language':'it','title':'SLA interval reconstruction after incident revisions','content':it,'output_cap':8192,
         'oracle':{'kind':'exact','expected':expected_it,'independent_check':'minute_sets','input':{'incidents':incidents,'maintenance':maintenance},'critical_rules':[]}},
        {'case_id':'DATA-EN','family':'DATA','language':'en','title':'Atomic snapshot across checksummed schema-migrated parts','content':en,'output_cap':4096,
         'oracle':{'kind':'exact','expected':expected_en,'nullable_paths':{'$.committed_records':'array'},'independent_check':'snapshot_assembly','input':{'manifest':manifest,'attempts':attempts},'critical_rules':[]}},
    ]


def check_independent(rows):
    """Minute sets and a separate receipt simulator crosscheck the literal references."""
    a, b = rows
    data = a['oracle']['input']; latest = {}
    for event in data['incidents']:
        if event['received'] > 60:
            continue
        old = latest.get(event['id'])
        if old is None or (event['revision'],event['received']) > (old['revision'],old['received']):
            latest[event['id']] = event
    outage = set()
    for event in latest.values():
        if event['state'] == 'ACTIVE':
            outage |= set(range(max(0,event['start']),min(60,event['end'])))
    maintenance = set()
    for event in data['maintenance']:
        if event['state'] == 'APPROVED':
            maintenance |= set(range(max(0,event['start']),min(60,event['end'])))
    def runs(values):
        result=[]
        for v in sorted(values):
            if result and result[-1][1]==v:result[-1][1]=v+1
            else:result.append([v,v+1])
        return result
    e=a['oracle']['expected']
    assert e['outage_union']==runs(outage) and e['excluded_maintenance']==runs(maintenance)
    assert e['chargeable_outages']==runs(outage-maintenance)
    assert e['eligible_minutes']==60-len(maintenance) and e['chargeable_down_minutes']==len(outage-maintenance)
    assert e['up_minutes']==len(set(range(60))-maintenance-outage)
    assert e['availability_bp_floor']==10000*e['up_minutes']//e['eligible_minutes']
    assert e['effective_incident_ids']==sorted(k for k,v in latest.items() if v['state']=='ACTIVE' and max(0,v['start'])<min(60,v['end']))
    assert e['cancelled_ids']==sorted(k for k,v in latest.items() if v['state']=='CANCELLED')
    assert e['ignored_after_cutoff']==sorted(v['record'] for v in data['incidents'] if v['received']>60)
    data=b['oracle']['input'];m=data['manifest'];parts={p['id']:p for p in m['parts']};accepted={};rejected=[]
    for x in sorted(data['attempts'],key=lambda x:x['seq']):
        part=parts.get(x['part']);reason=None;normalized=[]
        if x['received']>m['cutoff']:reason='AFTER_CUTOFF'
        elif part is None:reason='UNKNOWN_PART'
        elif x['snapshot']!=m['snapshot']:reason='SNAPSHOT'
        elif x['epoch']!=m['epoch']:reason='EPOCH'
        elif x['signature'] is not True:reason='SIGNATURE'
        elif x['actual_hash']!=part['hash']:reason='CHECKSUM'
        elif x['schema'] not in (2,3):reason='UNSUPPORTED_SCHEMA'
        else:
            keys={'index','key_id','minor_units'} if x['schema']==2 else {'index','key','value'}
            for row in x['rows']:
                key=row.get('key_id' if x['schema']==2 else 'key');value=row.get('minor_units' if x['schema']==2 else 'value')
                if set(row)!=keys or type(row.get('index')) is not int or type(key) is not str or not key or (value is not None and type(value) is not int):reason='ROW_SHAPE';break
                normalized.append({'index':row['index'],'key':key,'value':value})
            if reason is None and ([r['index'] for r in normalized]!=list(range(part['start'],part['end'])) or len({r['key'] for r in normalized})!=len(normalized)):reason='ROW_SHAPE'
            if reason is None and x['part'] in accepted:reason='DUPLICATE_PART'
        if reason:rejected.append({'attempt':x['attempt'],'reason':reason})
        else:accepted[x['part']]=(x['attempt'],normalized)
    e=b['oracle']['expected'];allrows=[z for _,rs in accepted.values() for z in rs]
    assert e['accepted_parts']==[{'part':p,'attempt':accepted[p][0]} for p in sorted(accepted)]
    assert e['rejected_attempts']==rejected and e['missing_parts']==sorted(set(parts)-set(accepted))
    assert e['staged_summary']=={'rows':len(allrows),'null_values':sum(z['value'] is None for z in allrows),'signed_value_sum':sum(z['value'] or 0 for z in allrows)}
    assert e['staged_coverage']==runs({z['index'] for z in allrows})
    assert e['status']=='BLOCKED' and e['committed_records'] is None and e['missing_parts']
    return {'minute_set_oracle':'PASS','independent_snapshot_simulator':'PASS'}
