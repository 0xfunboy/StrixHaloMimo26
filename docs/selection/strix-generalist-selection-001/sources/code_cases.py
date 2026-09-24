"""New synthetic multi-file repair tasks. References are withheld from inference."""
from __future__ import annotations
import json


def cases():
    initial_it = {
        'ledger.py': '''def delta(balances, account, amount):
    out = balances
    out[account] = out.get(account, 0) + amount
    return out
''',
        'batch.py': '''from ledger import delta

def apply_batch(balances, operations, seen):
    current = dict(balances)
    ids = seen
    for op in operations:
        if op['id'] in ids:
            continue
        current = delta(current, op['source'], -op['amount'])
        if current[op['source']] < 0:
            return balances, ids
        current = delta(current, op['destination'], op['amount'])
        ids.add(op['id'])
    return current, ids
'''}
    prompt_it = '''Fixture sintetica, nessun conto o servizio reale. Devi correggere una piccola libreria Python su DUE file, mantenendo le funzioni pubbliche. Non limitarti a spiegare i bug: restituisci i file corretti completi.
Contratto ledger.delta(balances, account, amount): balances e' un dict non vuoto di nomi di conto (stringhe non vuote) a saldi interi non negativi. account deve gia' esistere. amount e' un intero con segno; il saldo risultante non puo' essere negativo. bool non e' un intero valido. Ogni argomento invalido deve produrre ValueError. Restituisci un NUOVO dict; nessuna mutazione dell'input, anche in caso di errore.
Contratto batch.apply_batch(balances, operations, seen): seen e' un set di ID stringa non vuoti; operations e' una lista di dict. Valida balances e seen anche per una lista vuota. Ogni operazione deve avere un id stringa non vuoto. Se id e' gia' in seen o e' stato eseguito prima nello stesso batch, IGNORA tutta l'operazione dopo avere letto e validato il solo id: gli altri campi possono anche mancare. Altrimenti richiede source e destination distinti, esistenti, e amount intero strettamente positivo, non bool. Un trasferimento sposta amount da source a destination senza creare conti. Le operazioni sono sequenziali: le entrate precedenti possono finanziare uscite successive. Una operazione invalida, un tipo sbagliato, un conto ignoto o fondi insufficienti annullano l'intero batch mediante ValueError; nessun input puo' essere stato mutato. In successo restituisci una tuple (nuovi_saldi, nuovi_seen), rispettivamente dict e set, entrambi oggetti nuovi anche per batch vuoto.
Non importare librerie standard o terze parti; batch.py puo' importare soltanto ledger. Il chiamante puo' riusare balances, operations e seen dopo il ritorno o l'eccezione. Preserva anche i conti mai citati e conserva la somma dei saldi. Le chiavi extra nelle operazioni non influiscono sul trasferimento.
Risposta finale: un unico oggetto JSON con la sola chiave files, a sua volta con esattamente ledger.py e batch.py, i cui valori sono stringhe contenenti codice Python. Nessuna chiamata a tool reale.
File attuali:
''' + json.dumps(initial_it, ensure_ascii=False)
    # Two independent modules; test vectors describe externally observable contracts.
    ref_it = {
        'ledger.py': '''def valid_balances(balances):
    if type(balances) is not dict or not balances:
        raise ValueError('balances')
    for key, value in balances.items():
        if type(key) is not str or not key or type(value) is not int or value < 0:
            raise ValueError('balances')

def delta(balances, account, amount):
    valid_balances(balances)
    if type(account) is not str or account not in balances or type(amount) is not int:
        raise ValueError('delta')
    if balances[account] + amount < 0:
        raise ValueError('funds')
    out = dict(balances)
    out[account] += amount
    return out
''',
        'batch.py': '''from ledger import delta, valid_balances

def apply_batch(balances, operations, seen):
    valid_balances(balances)
    if type(operations) is not list or type(seen) is not set:
        raise ValueError('containers')
    if any(type(x) is not str or not x for x in seen):
        raise ValueError('seen')
    current = dict(balances)
    ids = set(seen)
    for op in operations:
        if type(op) is not dict or type(op.get('id')) is not str or not op['id']:
            raise ValueError('id')
        if op['id'] in ids:
            continue
        src = op.get('source')
        dst = op.get('destination')
        amount = op.get('amount')
        if type(src) is not str or type(dst) is not str or src == dst:
            raise ValueError('accounts')
        if src not in current or dst not in current or type(amount) is not int or amount <= 0:
            raise ValueError('transfer')
        current = delta(current, src, -amount)
        current = delta(current, dst, amount)
        ids.add(op['id'])
    return current, ids
'''}
    tests_it = [
        {'function':'ledger.delta','args':[{'a':10,'b':0},'a',-3],'expected':{'a':7,'b':0},'new_result_from_args':[0]},
        {'function':'ledger.delta','args':[{'a':10},'x',1],'error':'ValueError'},
        {'function':'ledger.delta','args':[{'a':10},'a',True],'error':'ValueError'},
        {'function':'ledger.delta','args':[{'a':2},'a',-3],'error':'ValueError'},
        {'function':'ledger.delta','args':[{'a':False},'a',1],'error':'ValueError'},
        {'function':'batch.apply_batch','args':[{'a':10,'b':0,'untouched':4},[{'id':'x','source':'a','destination':'b','amount':7},{'id':'y','source':'b','destination':'a','amount':2}],[]],'set_args':[2],'expected':[{'a':5,'b':5,'untouched':4},['x','y']],'new_pair_from_args':[0,2]},
        {'function':'batch.apply_batch','args':[{'a':10,'b':0},[{'id':'old'},{'id':'x','source':'a','destination':'b','amount':3},{'id':'x','amount':False}],['old']],'set_args':[2],'expected':[{'a':7,'b':3},['old','x']],'new_pair_from_args':[0,2]},
        {'function':'batch.apply_batch','args':[{'a':8,'b':0},[{'id':'ok','source':'a','destination':'b','amount':4},{'id':'bad','source':'b','destination':'a','amount':5}],[]],'set_args':[2],'error':'ValueError'},
        {'function':'batch.apply_batch','args':[{'a':8,'b':0},[{'id':'ok','source':'a','destination':'b','amount':4},{'id':'bad','source':'b','destination':'c','amount':1}],[]],'set_args':[2],'error':'ValueError'},
        {'function':'batch.apply_batch','args':[{'a':8,'b':0},[{'id':'x','source':'a','destination':'b','amount':True}],[]],'set_args':[2],'error':'ValueError'},
        {'function':'batch.apply_batch','args':[{'a':8,'b':0},[{'id':'x','source':'a','destination':'a','amount':1}],[]],'set_args':[2],'error':'ValueError'},
        {'function':'batch.apply_batch','args':[{'a':8,'b':0},[],['z']],'set_args':[2],'expected':[{'a':8,'b':0},['z']],'new_pair_from_args':[0,2]},
        {'function':'batch.apply_batch','args':[{'a':-1},[],[]],'set_args':[2],'error':'ValueError'},
        {'function':'batch.apply_batch','args':[{'a':1},[],['']],'set_args':[2],'error':'ValueError'},
        {'function':'batch.apply_batch','args':[{'a':2,'b':1},[{'id':'x','source':'a','destination':'b','amount':0}],[]],'set_args':[2],'error':'ValueError'},
        {'function':'batch.apply_batch','args':[{'a':2,'b':1},[{'id':'x','source':'a','destination':'b','amount':2},{'id':'z','source':'b','destination':'a','amount':3}],[]],'set_args':[2],'expected':[{'a':3,'b':0},['x','z']],'new_pair_from_args':[0,2]},
    ]
    initial_en = {
        'windows.py': '''def bucket_at(timestamp_ms, width_ms, origin_ms):
    return int((timestamp_ms - origin_ms) / width_ms)

def intersecting(start_ms, end_ms, width_ms, origin_ms):
    first = bucket_at(start_ms, width_ms, origin_ms)
    last = bucket_at(end_ms, width_ms, origin_ms)
    return list(range(first, last + 1))
''',
        'meter.py': '''from windows import bucket_at, intersecting

def summarize(events, width_ms, origin_ms, start_ms, end_ms):
    bins = {}
    for event in events:
        if start_ms <= event['timestamp_ms'] <= end_ms:
            i = bucket_at(event['timestamp_ms'], width_ms, origin_ms)
            bins[i] = bins.get(i, 0) + event['bytes']
    return {'buckets': [{'index': str(i), 'bytes': n} for i, n in sorted(bins.items())],
            'total_bytes': sum(bins.values()), 'total_events': len(events)}
'''}
    prompt_en = '''Synthetic library repair, not a real metering deployment. Correct BOTH Python files below while preserving their public functions. Return complete replacement code, not a diagnosis alone.
The grid consists of half-open intervals [origin_ms+i*width_ms, origin_ms+(i+1)*width_ms) for every integer i, including negative i. All times and width are Python integers but NOT bool. width_ms must be positive. bucket_at returns the integer index containing the time. intersecting returns increasing integer indices of every grid interval intersecting [start_ms,end_ms); return [] when start_ms==end_ms; start_ms>end_ms raises ValueError. These functions must validate their own arguments and raise ValueError for invalid ones. Use integer arithmetic, not floating point division, including for large integers beyond 2**53.
meter.summarize(events,width_ms,origin_ms,start_ms,end_ms) must validate all arguments and every event, including events outside the selected range. events must be a list of dictionaries. Every event requires timestamp_ms as integer-not-bool and bytes as nonnegative integer-not-bool. Extra event keys are ignored. Missing keys or invalid types raise ValueError. Each list entry is a distinct event, including exact duplicates. Include only events whose timestamp lies in [start_ms,end_ms). Return every intersecting grid bucket, including zero-activity buckets. Each bucket has exactly index (integer), bytes (integer sum), events (integer count). Return buckets in increasing index order. total_bytes and total_events equal the selected events, not all input events. Never mutate the input list or its dictionaries, including on failures. Valid empty intervals return an empty list of buckets and zero totals, after still validating the input events. For these fixtures the output has at most 100 buckets.
Do not import standard/third-party libraries; meter.py may import only windows. Final answer: one JSON object with only files, containing exactly windows.py and meter.py as Python source strings.
Current files:
''' + json.dumps(initial_en)
    ref_en = {
        'windows.py': '''def ints(*values):
    if any(type(v) is not int for v in values):
        raise ValueError('integer required')

def bucket_at(timestamp_ms, width_ms, origin_ms):
    ints(timestamp_ms, width_ms, origin_ms)
    if width_ms <= 0:
        raise ValueError('width')
    return (timestamp_ms - origin_ms) // width_ms

def intersecting(start_ms, end_ms, width_ms, origin_ms):
    ints(start_ms, end_ms, width_ms, origin_ms)
    if width_ms <= 0 or start_ms > end_ms:
        raise ValueError('bounds')
    if start_ms == end_ms:
        return []
    return list(range(bucket_at(start_ms, width_ms, origin_ms), bucket_at(end_ms - 1, width_ms, origin_ms) + 1))
''',
        'meter.py': '''from windows import bucket_at, intersecting

def summarize(events, width_ms, origin_ms, start_ms, end_ms):
    indices = intersecting(start_ms, end_ms, width_ms, origin_ms)
    if type(events) is not list:
        raise ValueError('events')
    bins = {i: {'index': i, 'bytes': 0, 'events': 0} for i in indices}
    total_bytes = 0
    total_events = 0
    for event in events:
        if type(event) is not dict or type(event.get('timestamp_ms')) is not int or type(event.get('bytes')) is not int or event['bytes'] < 0:
            raise ValueError('event')
        t = event['timestamp_ms']
        if start_ms <= t < end_ms:
            row = bins[bucket_at(t, width_ms, origin_ms)]
            row['bytes'] += event['bytes']
            row['events'] += 1
            total_bytes += event['bytes']
            total_events += 1
    return {'buckets': [bins[i] for i in indices], 'total_bytes': total_bytes, 'total_events': total_events}
'''}
    tests_en = [
        {'function':'windows.bucket_at','args':[-1,5,0],'expected':-1},
        {'function':'windows.bucket_at','args':[9007199254740995,2,0],'expected':4503599627370497},
        {'function':'windows.bucket_at','args':[False,5,0],'error':'ValueError'},
        {'function':'windows.intersecting','args':[-3,10,5,0],'expected':[-1,0,1]},
        {'function':'windows.intersecting','args':[0,0,5,0],'expected':[]},
        {'function':'windows.intersecting','args':[2,1,5,0],'error':'ValueError'},
        {'function':'windows.intersecting','args':[0,5,0,0],'error':'ValueError'},
        {'function':'meter.summarize','args':[[{'timestamp_ms':-3,'bytes':2},{'timestamp_ms':-1,'bytes':3},{'timestamp_ms':0,'bytes':5},{'timestamp_ms':8,'bytes':7},{'timestamp_ms':10,'bytes':99}],5,0,-3,10],
         'expected':{'buckets':[{'index':-1,'bytes':5,'events':2},{'index':0,'bytes':5,'events':1},{'index':1,'bytes':7,'events':1}],'total_bytes':17,'total_events':4}},
        {'function':'meter.summarize','args':[[],5,2,0,12],
         'expected':{'buckets':[{'index':-1,'bytes':0,'events':0},{'index':0,'bytes':0,'events':0},{'index':1,'bytes':0,'events':0}],'total_bytes':0,'total_events':0}},
        {'function':'meter.summarize','args':[[{'timestamp_ms':4,'bytes':2},{'timestamp_ms':4,'bytes':2}],5,0,0,5],
         'expected':{'buckets':[{'index':0,'bytes':4,'events':2}],'total_bytes':4,'total_events':2}},
        {'function':'meter.summarize','args':[[{'timestamp_ms':100,'bytes':-1}],5,0,0,5],'error':'ValueError'},
        {'function':'meter.summarize','args':[[{'timestamp_ms':1,'bytes':True}],5,0,0,5],'error':'ValueError'},
        {'function':'meter.summarize','args':[[{'timestamp_ms':1}],5,0,0,5],'error':'ValueError'},
        {'function':'meter.summarize','args':[[{'timestamp_ms':True,'bytes':2}],5,0,0,0],'error':'ValueError'},
        {'function':'meter.summarize','args':[[],5,0,0,0],'expected':{'buckets':[],'total_bytes':0,'total_events':0}},
        {'function':'meter.summarize','args':[[{'timestamp_ms':9007199254740995,'bytes':3}],2,9007199254740992,9007199254740992,9007199254740998],
         'expected':{'buckets':[{'index':0,'bytes':0,'events':0},{'index':1,'bytes':3,'events':1},{'index':2,'bytes':0,'events':0}],'total_bytes':3,'total_events':1}},
    ]
    return [
        {'case_id':'CODE-IT','family':'CODE','language':'it','title':'Atomic transfers across two modules','content':prompt_it,'output_cap':8192,
         'oracle':{'kind':'code','file_order':['ledger.py','batch.py'],'tests':tests_it,'reference':{'files':ref_it},'negative':{'files':initial_it},'critical_rules':[]}},
        {'case_id':'CODE-EN','family':'CODE','language':'en','title':'Half-open metering with large integer time','content':prompt_en,'output_cap':4096,
         'oracle':{'kind':'code','file_order':['windows.py','meter.py'],'tests':tests_en,'reference':{'files':ref_en},'negative':{'files':initial_en},'critical_rules':[]}},
    ]
