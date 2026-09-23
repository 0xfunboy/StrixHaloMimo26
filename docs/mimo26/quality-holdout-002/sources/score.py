"""Frozen CPU-only scoring. No output repair, model calls or candidate-code execution."""
from __future__ import annotations
import json
import math
from validate import same
from solvers import assess,key


def strict_parse(text):
    if not isinstance(text,str) or not text.strip():raise ValueError('empty response')
    if len(text)>65536:raise ValueError('response exceeds parser bound')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('duplicate key: '+k)
            out[k]=v
        return out
    def floating(token):
        value=float(token)
        if not math.isfinite(value):raise ValueError('nonfinite JSON number: '+token)
        return value
    def bad(token):raise ValueError('forbidden JSON constant: '+token)
    return json.loads(text.strip(),object_pairs_hook=pairs,parse_float=floating,parse_constant=bad)


def schema_errors(value,schema,path='$'):
    errors=[];types=schema['type'];types=[types] if isinstance(types,str) else types
    actual={type(None):'null',bool:'boolean',int:'integer',float:'number',str:'string',dict:'object',list:'array'}.get(type(value),'unsupported')
    if actual not in types:return [{'path':path,'issue':'type','expected':types,'actual':actual}]
    if 'enum' in schema and not any(same(value,x) for x in schema['enum']):errors.append({'path':path,'issue':'enum','actual':value})
    if isinstance(value,dict):
        props=schema.get('properties',{})
        for k in schema.get('required',[]):
            if k not in value:errors.append({'path':path+'.'+k,'issue':'missing key'})
        if schema.get('additionalProperties') is False:
            for k in value.keys()-props.keys():errors.append({'path':path+'.'+k,'issue':'unexpected key'})
        for k in value.keys()&props.keys():errors.extend(schema_errors(value[k],props[k],path+'.'+k))
    elif isinstance(value,list):
        for i,v in enumerate(value):errors.extend(schema_errors(v,schema['items'],path+f'[{i}]'))
    return sorted(errors,key=lambda x:(x['path'],x['issue']))


def differences(a,b,path='$'):
    if type(a) is not type(b):return [{'path':path,'issue':'type/value differs','expected':b,'actual':a}]
    if isinstance(b,dict):
        out=[]
        for k in sorted(b):
            if k not in a:out.append({'path':path+'.'+k,'issue':'missing value','expected':b[k]})
            else:out.extend(differences(a[k],b[k],path+'.'+k))
        for k in sorted(a.keys()-b.keys()):out.append({'path':path+'.'+k,'issue':'extra value','actual':a[k]})
        return out
    if isinstance(b,list):
        out=[]
        if len(a)!=len(b):out.append({'path':path,'issue':'list length','expected':len(b),'actual':len(a)})
        for i,(x,y) in enumerate(zip(a,b)):out.extend(differences(x,y,path+f'[{i}]'))
        return out
    return [] if a==b else [{'path':path,'issue':'value','expected':b,'actual':a}]


def json_invariants(v,oracle):
    checks=[]
    def ck(name,ok,actual=None,expected=None):checks.append({'invariant':name,'pass':bool(ok),'actual':actual,'required':expected})
    kind=oracle.get('invariant')
    if kind=='shipment_totals':
        rows=v['shipments'];total=sum(x['units'] for x in rows);by={}
        for r in rows:
            n=sum(x['qty'] for x in r['items']);ck(r['order_id']+': units equals item sum',r['units']==n,r['units'],n)
            by[r['warehouse']]=by.get(r['warehouse'],0)+r['units']
        ck('shipment count',v['totals']['orders']==len(rows),v['totals']['orders'],len(rows))
        ck('total units',v['totals']['units']==total,v['totals']['units'],total)
        ck('warehouse conservation',same(v['totals']['by_warehouse'],[{'warehouse':k,'units':n} for k,n in sorted(by.items())]))
    elif kind=='device_totals':
        ck('enabled_count',v['enabled_count']==sum(x['enabled'] for x in v['devices']))
        ck('quota_sum',v['quota_sum']==sum(x['quota'] for x in v['devices']))
    elif kind=='version_totals':
        ck('active_count',v['active_count']==len(v['active']))
        ck('active_quantity',v['active_quantity']==sum(x['quantity'] for x in v['active']))
        ids=[x['event_id'] for x in v['active']+v['deleted']]+v['discarded_event_ids']
        ck('each input event accounted exactly once',sorted(ids)==sorted(x['event_id'] for x in oracle['data']['events']))
    elif kind=='invoice_totals':
        for x in v['lines']:ck(x['id']+': net identity',x['remaining_net_cents']==x['gross_cents']-x['discount_cents']-x['refund_cents'])
        t=v['totals'];ck('net total',t['remaining_net_cents']==sum(x['remaining_net_cents'] for x in v['lines']))
        ck('tax total',t['line_tax_cents']==sum(x['tax_cents'] for x in v['lines']))
        payable=t['remaining_net_cents']+t['line_tax_cents']+t['shipping_net_cents']+t['shipping_tax_cents']-t['account_credit_cents']
        ck('payable identity',t['payable_cents']==payable,t['payable_cents'],payable)
    elif kind=='import_totals':
        ck('accepted count',v['counts']['accepted']==len(v['accepted']))
        ck('rejected count',v['counts']['rejected']==len(v['rejected']))
        ck('accepted quantity',v['accepted_qty']==sum(x['qty'] for x in v['accepted']))
        ck('row partition',sorted(x['row'] for x in v['accepted']+v['rejected'])==sorted(x['row'] for x in oracle['data']['records']))
    elif kind=='release_totals':
        source={x['lot']:x for x in oracle['data']['lots']}
        for x in v['lots']:
            ck(x['lot']+': release iff no failed guards',x['release']==(len(x['failed_guards'])==0))
            units=source.get(x['lot'],{}).get('ordered',-1) if x['release'] else 0
            ck(x['lot']+': units conditional on release',x['releasable_units']==units,x['releasable_units'],units)
        ck('release count',v['release_count']==sum(x['release'] for x in v['lots']))
        ck('releasable units',v['releasable_units']==sum(x['releasable_units'] for x in v['lots']))
    return checks


def critical(v,o):
    if not isinstance(v,dict):return []
    rule=o.get('critical_rule','');out=[]
    if rule=='release_failed_guard' and isinstance(v.get('lots'),list):
        expected={x['lot']:x for x in o['expected']['lots']}
        for x in v['lots']:
            if isinstance(x,dict) and x.get('release') is True and x.get('lot') in expected and expected[x['lot']]['release'] is False:
                out.append('FALSE_RELEASE_WITH_FAILED_MANDATORY_GUARD:'+x['lot'])
    if rule in ('unrun_reported_pass','denied_reported_approved'):
        claim='functional_validation' if rule=='unrun_reported_pass' else 'export_permission'
        prohibited='PASS' if rule=='unrun_reported_pass' else 'APPROVED'
        claims=v.get('claims')
        if isinstance(claims,dict) and isinstance(claims.get(claim),dict) and claims[claim].get('value')==prohibited:out.append(rule.upper())
    return out


def constraint_dimensions(v,o):
    spec=o['spec'];exp=o['expected'];kind=spec['kind'];declared=v['status']
    result={'feasible':False,'violated_constraints':[],'recalculated':None,'declared_total_mismatches':[],
            'optimality':False,'tie_break':False,'oracle_status':exp['status']}
    if declared=='INFEASIBLE':
        empty={'status':'INFEASIBLE'}
        if kind=='selection':empty.update(ids=[],cost=None,risk=None,value=None)
        elif kind=='route':empty.update(path=[],cost=None,risk=None,time=None)
        else:empty.update(assignments=[],cost=None,makespan=None)
        shape_ok=same(v,empty)
        result.update(feasible=exp['status']=='INFEASIBLE' and shape_ok,optimality=exp['status']=='INFEASIBLE',tie_break=exp['status']=='INFEASIBLE',infeasibility_claim_proved=exp['status']=='INFEASIBLE')
        if not shape_ok:result['violated_constraints'].append('INFEASIBLE must have empty decisions and null totals')
        if exp['status']!='INFEASIBLE':result['violated_constraints'].append('false INFEASIBLE: exact oracle has feasible solutions')
        return result
    if declared!='OPTIMAL':result['violated_constraints']=['status must be OPTIMAL or INFEASIBLE'];return result
    computed,errors=assess(spec,v)
    if kind=='selection' and v['ids']!=sorted(v['ids']):errors.append('ID list not sorted lexicographically')
    if kind=='assignment' and v['assignments']!=sorted(v['assignments'],key=lambda x:x['job']):errors.append('assignment list not in job-id order')
    result['recalculated']=computed;result['violated_constraints']=errors;result['feasible']=not errors
    if computed is not None:
        numeric=('cost','risk','value') if kind=='selection' else ('cost','risk','time') if kind=='route' else ('cost','makespan')
        result['declared_total_mismatches']=[{'field':x,'declared':v[x],'recalculated':computed[x]} for x in numeric if not same(v[x],computed[x])]
        if not errors and exp['status']=='OPTIMAL':
            candidate_key=key(spec,computed);oracle_key=key(spec,exp)
            result['optimality']=candidate_key[0]==oracle_key[0]
            result['tie_break']=candidate_key[1:]==oracle_key[1:]
            result['candidate_objective']=json.loads(json.dumps(candidate_key));result['oracle_objective']=json.loads(json.dumps(oracle_key))
    if exp['status']=='INFEASIBLE':result['violated_constraints'].append('oracle proves no feasible complete solution')
    return result


def verdict(text,oracle,completion_status='COMPLETE'):
    d={'parsing':False,'schema':False}
    if completion_status!='COMPLETE':return {'status':completion_status,'reason':'not naturally completed','critical_violations':[],'diagnostics':d}
    try:v=strict_parse(text)
    except (ValueError,TypeError,RecursionError,OverflowError) as exc:
        return {'status':'FAIL_FORMAT','reason':str(exc)[:1000],'critical_violations':[],'diagnostics':{**d,'parse_error':str(exc)[:1000]}}
    d['parsing']=True;se=schema_errors(v,oracle['schema']);d['schema']=not se;d['schema_errors']=se
    crit=critical(v,oracle)
    if se:return {'status':'FAIL_FORMAT','parsed':v,'critical_violations':crit,'diagnostics':d}
    if oracle['kind']=='JSON':
        diff=differences(v,oracle['expected']);checks=json_invariants(v,oracle)
        d.update(values=not diff,value_errors=diff,invariants=all(x['pass'] for x in checks),invariant_checks=checks)
        passed=not diff and d['invariants']
    elif oracle['kind']=='EVIDENCE':
        all_ids=set(oracle['all_document_ids']);claims={}
        for name,expected in oracle['claims'].items():
            proposed=v['claims'][name];ids=proposed['citations'];citations=set(ids)
            relevant=set(expected.get('relevant_ids',[])) or set().union(*(set(s) for s in expected['allowed_sets']))
            absent=sorted(citations-all_ids);irrelevant=sorted(citations-relevant)
            suff=any(set(s)<=citations for s in expected['allowed_sets'])
            claims[name]={'value_correct':same(proposed['value'],expected['value']),'expected_value':expected['value'],'actual_value':proposed['value'],
                'citations_exist':not absent,'citations_relevant':not irrelevant,'citations_sufficient':suff,'duplicates':len(ids)!=len(citations),
                'nonexistent_ids':absent,'irrelevant_or_superseded_ids':irrelevant,'actual_citations':ids,
                'sufficient_alternatives':expected['allowed_sets']}
            claims[name]['pass']=all((claims[name]['value_correct'],not absent,not irrelevant,suff,not claims[name]['duplicates']))
        d['claims']=claims;d['claim_coverage_complete']=all(x['pass'] for x in claims.values());passed=d['claim_coverage_complete']
    elif oracle['kind']=='CONSTRAINT':
        con=constraint_dimensions(v,oracle);d['constraint']=con
        passed=con['feasible'] and con['optimality'] and con['tie_break'] and not con['declared_total_mismatches'] and not con['violated_constraints']
    else:raise ValueError('unknown oracle kind')
    return {'status':'PASS' if passed else 'FAIL_SEMANTIC','parsed':v,'critical_violations':crit,'diagnostics':d}
