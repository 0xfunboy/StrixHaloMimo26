"""Bounded CPU checks. Candidate/reference code is delegated only to rootless Podman."""
from __future__ import annotations
import argparse
import ast
import copy
import json
from pathlib import Path
import tempfile
from common import atomic,completion_state,digest,split_reasoning
from validate import verdict,parse,sandbox,schema,sanity_verdict
import panel,data_cases,math_cases,science_cases


def reference(o):
    if o['kind']=='code':return o['reference']
    if o['kind']=='evidence':return {'claims':{k:{'value':v['value'],'citations':v['allowed_sets'][0]} for k,v in o['claims'].items()}}
    return o['expected']


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    checks=[]
    def ck(name,value):
        if not value:raise AssertionError(name)
        checks.append({'name':name,'pass':True})
    rows=panel.cases();ck('twelve_new_cases',len(rows)==12);ck('budget_73728',sum(r['output_cap'] for r in rows)==73728)
    for family in panel.FAMILIES:ck('family_'+family,sum(r['family']==family for r in rows)==2)
    independent={'data':data_cases.check_independent(data_cases.cases()),'math':math_cases.check_independent(),'science':science_cases.check_independent()}
    for path in Path(__file__).parent.glob('*.py'):
        ast.parse(path.read_text());ck('source_syntax_'+path.name,True)
    pr=sandbox({'mode':'probe'})
    ck('sandbox_probe_return',pr.get('status')=='PASS')
    v=pr['probe'];ck('unprivileged_uid',v['uid']==65534);ck('host_home_not_mounted',v['host_home_present'] is False)
    ck('gpu_not_exposed',not any(d in v['devices'] for d in ['dri','kfd','nvidia0']))
    ck('network_cannot_access_resident',all(c!=0 for c in v['network_connect_codes'].values()))
    ck('capabilities_empty',any(x.split(':',1)[1].strip()=='0000000000000000' for x in v['capability_status'] if x.startswith('CapEff:')))
    ck('no_new_privileges',any(x.split(':',1)[1].strip()=='1' for x in v['capability_status'] if x.startswith('NoNewPrivs:')))
    evaluations={}
    for row in rows:
        o=row['oracle'];ref=reference(o);text=json.dumps(ref,ensure_ascii=False,allow_nan=False)
        result=verdict(text,o);evaluations[row['case_id']]=result
        ck(row['case_id']+'_independent_reference_pass',result['status']=='PASS')
        ck(row['case_id']+'_empty_fails',verdict('',o)['status']=='FAIL_FORMAT')
        ck(row['case_id']+'_extra_key_rejected',verdict(json.dumps({**ref,'extra':0}),o)['status']=='FAIL_FORMAT')
        ck(row['case_id']+'_cap_never_promoted',verdict(text,o,'INCOMPLETE_OUTPUT_CAP')['status']=='INCOMPLETE_OUTPUT_CAP')
        if o['kind']=='code':
            bad=verdict(json.dumps(o['negative']),o)
            ck(row['case_id']+'_original_bugs_detected',bad['status']=='FAIL_CODE_TEST')
            ck(row['case_id']+'_positive_tests_executed',len(result['diagnostics']['execution']['tests'])>=16)
        elif o['kind']=='evidence':
            for name,item in o['claims'].items():
                for i,allowed in enumerate(item['allowed_sets']):
                    alt=copy.deepcopy(ref);alt['claims'][name]['citations']=allowed
                    ck(row['case_id']+name+'_alternative_'+str(i),verdict(json.dumps(alt),o)['status']=='PASS')
                bad=copy.deepcopy(ref);bad['claims'][name]['citations']=[]
                ck(row['case_id']+name+'_missing_evidence',verdict(json.dumps(bad),o)['status']=='FAIL_SEMANTIC')
                bad=copy.deepcopy(ref);bad['claims'][name]['citations']=['FAKE-ID']
                ck(row['case_id']+name+'_fake_evidence',verdict(json.dumps(bad),o)['status']=='FAIL_SEMANTIC')
                irrelevant=next(x for x in o['all_ids'] if x not in item['relevant_ids'])
                bad=copy.deepcopy(ref);bad['claims'][name]['citations']=[irrelevant]
                ck(row['case_id']+name+'_real_but_irrelevant',verdict(json.dumps(bad),o)['status']=='FAIL_SEMANTIC')
                bad=copy.deepcopy(ref);bad['claims'][name]['citations']*=2
                ck(row['case_id']+name+'_duplicate_evidence',verdict(json.dumps(bad),o)['status']=='FAIL_SEMANTIC')
        else:
            for name,value in ref.items():
                if type(value) in (int,float):
                    bad=copy.deepcopy(ref);bad[name]=value+1
                    ck(row['case_id']+name+'_wrong_number',verdict(json.dumps(bad),o)['status']=='FAIL_SEMANTIC')
                    bad[name]=True
                    ck(row['case_id']+name+'_bool_not_number',verdict(json.dumps(bad),o)['status']=='FAIL_FORMAT')
    for text in ['{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}','{"x":1e999}','```json\n{}\n```','{} trailing','{"x":']:
        try:parse(text);passed=False
        except (ValueError,TypeError):passed=True
        ck('strict_parser_'+text,passed)
    q={'think_open_id':10,'think_close_id':11,'eos_ids':[12],'thinking_prefix_open':True}
    m={**q,'thinking_prefix_open':False}
    x=split_reasoning('reason</think>{"ok":true}',[1,2,11,3,4,12],True,q)
    ck('qwen_prefilled_reasoning',x['reasoning_text']=='reason' and x['final_text']=='{"ok":true}' and x['reasoning_tokens_native']==2 and x['final_tokens_native']==2)
    x=split_reasoning('<think>reason</think>{}',[10,0,2,11,3,12],True,m)
    ck('mimo_generated_reasoning_zero_id_preserved',x['reasoning_tokens_native']==2 and x['final_text']=='{}')
    x=split_reasoning('still thinking',[1,2],True,q)
    ck('unclosed_reasoning_has_no_final',x['reasoning_closed'] is False and x['final_text']=='')
    ck('cap_not_final',completion_state('length',4096,4096,'{}','panel')=='INCOMPLETE_OUTPUT_CAP')
    ck('eos_without_final',completion_state('eos',50,4096,'','panel')=='INCOMPLETE_NO_FINAL')
    ck('benchmark_short_preserved',completion_state('eos',50,128,'text','benchmark')=='SHORT_OUTPUT')
    ck('benchmark_cap_valid',completion_state('limit',128,128,'text','benchmark')=='VALID_CAP')
    with tempfile.TemporaryDirectory(prefix='gs001-cpu-') as tmp:
        path=Path(tmp)/'result.json';atomic(path,{'n':1},exclusive=True)
        try:atomic(path,{'n':2},exclusive=True);blocked=False
        except FileExistsError:blocked=True
        ck('atomic_no_overwrite',blocked and json.loads(path.read_text())=={'n':1})
    result={'schema':'generalist-cpu-preflight-v1','status':'PASS','checks':checks,'independent_oracles':independent,'reference_evaluations':evaluations,'sandbox_probe':pr,'new_inference_calls':0}
    atomic(args.output,result)
    print(json.dumps({'status':'CPU_TEST_PASS','checks':len(checks),'cases':len(rows),'sandbox':'PASS','new_inference_calls':0}))

if __name__=='__main__':main()
