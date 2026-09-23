"""Pre-GPU positive/negative coverage; does not load models or run generated code on host."""
from __future__ import annotations
import ast
import collections
import copy
import itertools
import json
import tempfile
from pathlib import Path
from common import atomic,completion_state,digest,ids_sha,read_jsonl,sha
from panel import make_panel
from score import strict_parse,verdict,schema_errors
from validate import sandbox,sanity_verdict,same
from solvers import assess,key
from native_audit import paired_state,check_record

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/mimo26/quality-holdout-002')
HERE=Path(__file__).resolve().parent
checks=[]


def test(name,condition,detail=None):
    checks.append({'test':name,'pass':bool(condition),'detail':detail})
    if not condition:raise AssertionError(name+': '+str(detail))


def scored(value,o):return verdict(json.dumps(value,ensure_ascii=False,allow_nan=False),o)


def leaf_paths(v,path=()):
    if isinstance(v,dict):
        for k,x in v.items():yield from leaf_paths(x,path+(k,))
    elif isinstance(v,list):
        for k,x in enumerate(v):yield from leaf_paths(x,path+(k,))
    else:yield path,v


def change(v,path,new):
    v=copy.deepcopy(v);cur=v
    for key0 in path[:-1]:cur=cur[key0]
    cur[path[-1]]=new
    return v


def native_fixture(case,arm,run):
    ids=case['input_token_ids'];output=[4,9,12];count=3
    rec={'campaign':'QUALITY-HOLDOUT-002','arm':arm,'run_id':run.name,'phase':'panel','case_id':case['case_id'],
         'request_id':run.name+'/'+arm+'/panel/'+case['case_id'],'source_index_sha256':'mock-index','input_ids_provided':ids,
         'input_ids_sha256':ids_sha(ids),'rendered_text':case['rendered_text'],'messages':case['messages'],'output_cap':case['output_cap'],
         'sampling':{'temperature':0,'seed':1,'ignore_eos':False,'thinking':False},'completion_status':'COMPLETE',
         'output_token_ids':output,'output_tokens':count,'cache_reused_tokens':0,'cache_gate_pass':True,'native_prompt_processed':len(ids),
         'collector_consistency_pass':True,'diagnostic_wall_s':1,'final_text':'{}','finish_reason':'eos' if arm=='A' else 'stop'}
    if arm=='A':rec['native_response']={'stop':True,'content':'{}','tokens':output,'tokens_predicted':count,'tokens_evaluated':len(ids),'stop_type':'eos',
        'timings':{'predicted_n':count,'cache_n':0,'prompt_n':len(ids)}}
    else:
        rec['native_input_ids_echoed']=ids
        rec['native_response']={'finished':True,'prompt_token_ids':ids,'num_cached_tokens':0,'metrics':{'is_corrupted':False},
            'outputs':[{'token_ids':output,'text':'{}','finish_reason':'stop'}]}
    rec['record_sha256']=digest(rec)
    return rec


def main():
    cases,oracles=make_panel()
    test('18 unique cases and total cap12288',len(cases)==18 and len({c['case_id'] for c in cases})==18 and sum(c['output_cap'] for c in cases)==12288)
    for c,o in zip(cases,oracles):
        cid=c['case_id'];v=o['expected']
        test(cid+': independent reference accepted',scored(v,o)['status']=='PASS')
        reordered=dict(reversed(list(v.items())))
        test(cid+': object-key order immaterial',scored(reordered,o)['status']=='PASS')
        wrong=copy.deepcopy(v);name=next(iter(wrong));wrong[name+'_typo']=wrong.pop(name)
        test(cid+': correct values wrong key rejected',scored(wrong,o)['status']=='FAIL_FORMAT')
        wrong=copy.deepcopy(v);wrong['not_in_contract']=0
        test(cid+': extra key rejected',scored(wrong,o)['status']=='FAIL_FORMAT')
        for text,label in [('', 'empty'),('{','truncated'),('[]','wrong root'),('true','boolean root'),('```json\n'+json.dumps(v)+'\n```','markdown fence'),('{"x":1,"x":2}','duplicate keys'),('{"x":NaN}','NaN'),('{"x":Infinity}','Infinity'),('{"x":1e999}','overflow to infinity')]:
            test(cid+': '+label,verdict(text,o)['status']=='FAIL_FORMAT')
        for state in ('INCOMPLETE_OUTPUT_CAP','TIMEOUT','TECHNICAL_ERROR','NOT_RUN','VALIDATOR_BLOCKED','CASE_INVALID'):
            test(cid+': preserve '+state,verdict(json.dumps(v),o,state)['status']==state)
        if c['family']=='JSON':
            for path,value in leaf_paths(v):
                mutated=not value if type(value) is bool else value+1 if type(value) is int else 'wrong-value' if value is None else value+'-wrong'
                bad=scored(change(v,path,mutated),o)
                test(cid+': exact value '+str(path),bad['status']!='PASS')
                if type(value) is int:
                    test(cid+': boolean is not integer '+str(path),scored(change(v,path,True),o)['status']=='FAIL_FORMAT')
                    test(cid+': floating integer is not integer '+str(path),scored(change(v,path,float(value)),o)['status']=='FAIL_FORMAT')
            test(cid+': invariants recorded separately',bool(scored(v,o)['diagnostics']['invariant_checks']))
        elif c['family']=='EVIDENCE':
            names=list(o['claims'])
            for choices in itertools.product(*(x['allowed_sets'] for x in o['claims'].values())):
                alternative=copy.deepcopy(v)
                for name,ids in zip(names,choices):alternative['claims'][name]['citations']=list(reversed(ids))
                test(cid+': equivalent sufficient sets '+str(choices),scored(alternative,o)['status']=='PASS')
            for name,claim in o['claims'].items():
                reference=v['claims'][name]['citations']
                def variant(ids):
                    r=copy.deepcopy(v);r['claims'][name]['citations']=ids;return r
                irrelevant=next(x for x in o['all_document_ids'] if x not in claim['relevant_ids'])
                for label,ids in [('missing',[]),('nonexistent',['NO_SUCH_SOURCE']),('existing irrelevant',[irrelevant]),('all documents',o['all_document_ids']),('duplicate',reference+reference[:1])]:
                    res=scored(variant(ids),o)
                    test(cid+': '+name+' '+label,res['status']=='FAIL_SEMANTIC',res['diagnostics']['claims'][name])
                for minimal in claim['allowed_sets']:
                    if len(minimal)>1:
                        for i in range(len(minimal)):
                            res=scored(variant(minimal[:i]+minimal[i+1:]),o)
                            test(cid+': '+name+' insufficient subset '+str(i),not res['diagnostics']['claims'][name]['citations_sufficient'])
                for extra in claim['relevant_ids']:
                    res=scored(variant(sorted(set(reference)|{extra})),o)
                    test(cid+': '+name+' optional pertinent evidence '+extra,res['status']=='PASS')
                wrong=copy.deepcopy(v);val=wrong['claims'][name]['value'];wrong['claims'][name]['value']=val+1 if type(val) is int else 'UNSUPPORTED'
                test(cid+': '+name+' correct evidence false value',scored(wrong,o)['status']=='FAIL_SEMANTIC')
        else:
            proof=o['oracle_proof'];test(cid+': two independent exact algorithms agree',proof['agreement'] and proof['primary']['feasible_count']==proof['independent']['feasible_count'])
            for i,feasible in enumerate(o['feasible_solutions']):
                r=scored(feasible,o);test(cid+': feasible plan '+str(i)+' judged by full objective',(r['status']=='PASS')==same(feasible,v))
            if v['status']=='OPTIMAL':
                wrong=copy.deepcopy(v);wrong['cost']+=1
                res=scored(wrong,o)
                test(cid+': declared total never replaced',res['status']=='FAIL_SEMANTIC' and res['parsed']['cost']==wrong['cost'] and bool(res['diagnostics']['constraint']['declared_total_mismatches']))
                empty={'status':'INFEASIBLE'}
                if o['spec']['kind']=='selection':empty.update(ids=[],cost=None,risk=None,value=None)
                elif o['spec']['kind']=='route':empty.update(path=[],cost=None,risk=None,time=None)
                else:empty.update(assignments=[],cost=None,makespan=None)
                test(cid+': unproved INFEASIBLE rejected',scored(empty,o)['status']=='FAIL_SEMANTIC')
                candidate=copy.deepcopy(v)
                if o['spec']['kind']=='selection':candidate['ids']=[x['id'] for x in o['spec']['items']]
                elif o['spec']['kind']=='route':candidate['path']=[o['spec']['start'],o['spec']['end']]
                else:candidate['assignments']=[{**x,'worker':'W-A','slot':0} for x in v['assignments']]
                res=scored(candidate,o)
                test(cid+': infeasible proposed plan rejected',res['status']=='FAIL_SEMANTIC' and bool(res['diagnostics']['constraint']['violated_constraints']))
            else:
                test(cid+': infeasibility enumeration has zero feasible plans',proof['primary']['feasible_count']==0)
                bad={'status':'OPTIMAL','assignments':[{'job':j['id'],'worker':j['eligible'][0],'slot':j['slots'][0]} for j in o['spec']['jobs']],'cost':9,'makespan':3}
                test(cid+': forced specialist schedule rejected',scored(bad,o)['status']=='FAIL_SEMANTIC')
        if o.get('critical_rule')=='release_failed_guard':
            wrong=copy.deepcopy(v);wrong['lots'][1]['release']=True
            test(cid+': preregistered false authorization detected',bool(scored(wrong,o)['critical_violations']))
        if o.get('critical_rule')=='unrun_reported_pass':
            wrong=copy.deepcopy(v);wrong['claims']['functional_validation']['value']='PASS'
            test(cid+': unrun test falsely passed detected',bool(scored(wrong,o)['critical_violations']))
        if o.get('critical_rule')=='denied_reported_approved':
            wrong=copy.deepcopy(v);wrong['claims']['export_permission']['value']='APPROVED'
            test(cid+': denied export falsely approved detected',bool(scored(wrong,o)['critical_violations']))
    # Inspect the actual tokenized build rather than assuming source-text length.
    built=read_jsonl(ROOT/'cases.jsonl');expected=read_jsonl(ROOT/'expected.jsonl')
    test('tokenized case IDs preserve panel order',[x['case_id'] for x in built]==[x['case_id'] for x in cases])
    for c,e,b in zip(cases,expected,built):
        test(c['case_id']+': messages unchanged by tokenization',c['messages']==b['messages'])
        test(c['case_id']+': exact context cap plus256 margin',0<b['input_tokens'] and b['input_tokens']+b['output_cap']+256<=4096)
        test(c['case_id']+': native-input IDs frozen consistently',b['input_tokens']==len(b['input_token_ids']) and b['input_token_ids_sha256']==ids_sha(b['input_token_ids']))
        test(c['case_id']+': correct reference fits with64 spare',e['reference_token_count']+64<=b['output_cap'])
        test(c['case_id']+': written oracle same as pre-GPU source',same({k:v for k,v in e.items() if k!='reference_token_count'},oracles[cases.index(c)]))
    for a in ('PASS','FAIL_FORMAT','FAIL_SEMANTIC','TIMEOUT','INCOMPLETE_OUTPUT_CAP','NOT_RUN'):
        for b in ('PASS','FAIL_FORMAT','FAIL_SEMANTIC','TIMEOUT','INCOMPLETE_OUTPUT_CAP','NOT_RUN'):
            outcome=paired_state(a,b)
            expected_other=a in ('TIMEOUT','INCOMPLETE_OUTPUT_CAP','NOT_RUN') or b in ('TIMEOUT','INCOMPLETE_OUTPUT_CAP','NOT_RUN')
            test('pair denominator '+a+'/'+b,(outcome=='OTHER_STATES')==expected_other)
    for finish,n,cap,want in [('eos',7,512,'COMPLETE'),('stop',7,512,'COMPLETE'),('limit',512,512,'INCOMPLETE_OUTPUT_CAP'),('length',512,512,'INCOMPLETE_OUTPUT_CAP'),(None,0,512,'TECHNICAL_ERROR'),('stop',512,512,'INCOMPLETE_OUTPUT_CAP')]:
        test('completion boundary '+str((finish,n)),completion_state(finish,n,cap)==want)
    with tempfile.TemporaryDirectory(prefix='qh002-cpu-') as temp:
        run=Path(temp)/'mock';run.mkdir();p=run/'exclusive.json'
        atomic(p,{'value':1},exclusive=True)
        try:atomic(p,{'value':2},exclusive=True);refused=False
        except FileExistsError:refused=True
        test('atomic publication refuses replacement',refused and json.loads(p.read_text())=={'value':1})
        test('atomic publication leaves no temp residue',not list(run.glob('.exclusive*')))
        case=built[0]
        for arm in ('A','B'):
            rec=native_fixture(case,arm,run);dest=run/'requests'/('panel__'+case['case_id'])/'result.json'
            atomic(dest,rec)
            test(arm+': simulated native record valid',not check_record(rec,case,arm,'mock-index',run,'panel'))
            for label,field,value in [('cap changed','output_cap',1),('cache reused','cache_reused_tokens',1),('missing native IDs','output_token_ids',[]),('deadline exceeded','diagnostic_wall_s',case['timeout_s']+1)]:
                bad=copy.deepcopy(rec);bad[field]=value;bad['record_sha256']=digest({k:v for k,v in bad.items() if k!='record_sha256'});atomic(dest,bad)
                test(arm+': native '+label,bool(check_record(bad,case,arm,'mock-index',run,'panel')))
    for p in HERE.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    test('new sources all parse',True)
    for f in ('adapter_a.py','adapter_b.py'):
        text=(HERE/f).read_text()
        test(f+': no hidden expected supplied','expected.jsonl' not in text and 'from solvers' not in text and 'from score' not in text)
        test(f+': qualified collector unchanged',(HERE/f).read_bytes()==(ROOT.parent/'quality-retention-001/sources'/f).read_bytes())
    from evaluate import decision,outputs
    for family in ('JSON','EVIDENCE','CONSTRAINT'):
        fake=[{'case_id':'mock-'+str(i),'A':{'status':'PASS','critical_violations':[]},'B':{'status':'PASS','critical_violations':[]}} for i in range(6)]
        d=decision(family,fake)
        test(family+': all PASS only proposes supervision',d['arms']['A']['decision']=='SCOPED_SUPERVISED_PILOT_PROPOSAL_ONLY')
        fake[0]['A']['status']='FAIL_SEMANTIC'
        test(family+': successful restore cannot turn semantic FAIL into pilot',decision(family,fake)['arms']['A']['decision']=='CONTAIN_OBSERVED_ERRORS_BEFORE_FAMILY_PILOT')
        fake[0]['A']['status']='NOT_RUN'
        test(family+': incomplete denominator prevents family pilot',decision(family,fake)['arms']['A']['decision']=='EVIDENCE_INCOMPLETE_NO_FAMILY_PILOT_PROPOSAL')
    for c,o in zip(cases,oracles):
        first=scored(o['expected'],o);second=scored(o['expected'],o)
        test(c['case_id']+': CPU scoring reproducible and JSON serializable',same(first,second) and same(first,json.loads(json.dumps(first))))
    probe=sandbox({'mode':'probe'});test('sandbox isolation verified',probe.get('probe',{}).get('pass') is True,probe)
    good='def clamp(x, lo, hi):\n    return lo if x < lo else hi if x > hi else x\n'
    test('sanity code executes only in isolated Podman',sanity_verdict('code_clamp',good)['status']=='PASS')
    test('wrong sanity code rejected',sanity_verdict('code_clamp','def clamp(x, lo, hi):\n    return x\n')['status']=='FAIL_CODE_TEST')
    test('unsafe code not executed on host',sanity_verdict('code_clamp','import os\ndef clamp(x, lo, hi):\n    return x\n')['status']=='FAIL_CODE_TEST')
    atomic(ROOT/'preflight/cpu-tests.json',{'schema':'mimo26-holdout-cpu-tests-v1','status':'PASS','checks':checks,'checks_passed':len(checks),
        'coverage':'all positive references; field-level JSON negatives; equivalent citation sets and missing/irrelevant/insufficient evidence; all feasible constraint solutions and targeted infeasibility/totals; pairing/caps/native contract/isolation',
        'oracle_proofs':{e['case_id']:e['oracle_proof'] for e in oracles if e['kind']=='CONSTRAINT'},
        'sandbox_probe':probe,'new_inference_calls':0,'candidate_code_execution':'ONLY_ISOLATED_ROOTLESS_PODMAN'})
    print(json.dumps({'status':'HOLDOUT_CPU_TEST_PASS','checks':len(checks),'cases':len(cases),'new_inference_calls':0}))


if __name__=='__main__':main()
