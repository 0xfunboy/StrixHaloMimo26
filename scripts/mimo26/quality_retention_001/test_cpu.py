"""CPU-only pre-registration tests; no imports or starts of inference engines."""
from __future__ import annotations
import argparse
import copy
import json
import sys
from pathlib import Path
from common import atomic,completion_state,digest,ids_sha,read_jsonl,verify_freeze
from panel import make_panel,sanity_panel
from validate import extract,same,sandbox,strict_json,verdict,sanity_verdict


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path);ap.add_argument('--receipt',type=Path);a=ap.parse_args()
    cases,expected=make_panel();checks=[]
    def check(name,condition,detail=None):
        checks.append({'name':name,'pass':bool(condition),'detail':detail})
        if not condition:raise AssertionError(name+': '+str(detail))
    check('24_unique_cases',len(cases)==24 and len({c['case_id'] for c in cases})==24)
    families={f:sum(c['family']==f for c in cases) for f in {c['family'] for c in cases}}
    check('six_families_four_each',len(families)==6 and set(families.values())=={4},families)
    check('language_balance',sum(c['language']=='it' for c in cases)==12 and sum(c['language']=='en' for c in cases)==12)
    check('caps_preregistered',sum(c['output_cap'] for c in cases)==16384 and all(c['output_cap'] in (512,1024,1536) for c in cases))
    probe=sandbox({'mode':'probe'})
    check('existing_sandbox_no_host_no_network_limits',probe.get('probe',{}).get('pass') is True,probe)
    def mutate(v):
        if isinstance(v,dict):
            out=copy.deepcopy(v);k=next(iter(out));out[k]=mutate(out[k]);return out
        if isinstance(v,list):return v+['deliberately_wrong']
        if type(v) is bool:return not v
        if type(v) is int:return v+1
        if type(v) is str:return v+'_WRONG'
        return 'not_null'
    for oracle in expected:
        cid=oracle['case_id']
        reference=oracle['reference_code'] if oracle['kind']=='code' else json.dumps(oracle['expected'],ensure_ascii=False)
        r=verdict(reference,oracle)
        check(cid+'_independent_reference_pass',r['status']=='PASS',r)
        wrong=oracle['counterexample'] if oracle['kind']=='code' else json.dumps(mutate(oracle['expected']))
        r=verdict(wrong,oracle)
        check(cid+'_deliberate_counterexample_rejected',r['status'].startswith('FAIL_'),r)
        check(cid+'_empty_rejected',verdict('',oracle)['status']=='FAIL_FORMAT')
        check(cid+'_cap_never_scored_pass',verdict(reference,oracle,'INCOMPLETE_OUTPUT_CAP')['status']=='INCOMPLETE_OUTPUT_CAP')
    sample=next(o for o in expected if o['case_id']=='STRUCT-01')
    for label,payload in [('invalid_json','{"id":'),('missing_key',json.dumps({k:v for k,v in sample['expected'].items() if k!='id'})),
                          ('wrong_type_bool_as_integer',json.dumps({**sample['expected'],'total_cents':True})),
                          ('extra_key',json.dumps({**sample['expected'],'extra':0})),('duplicate_key','{"x":1,"x":2}'),
                          ('truncated_fence','```json\n{}'),('commentary','Here is the result:\n'+json.dumps(sample['expected']))]:
        check(label,verdict(payload,sample)['status']=='FAIL_FORMAT')
    check('valid_json_fence',verdict('```json\n'+json.dumps(sample['expected'])+'\n```',sample)['status']=='PASS')
    check('type_equality_not_python_bool_coercion',not same(True,1) and not same([1],[True]))
    check('termination_without_result',completion_state(None,0,512,False)=='TECHNICAL_ERROR')
    check('short_natural_output_is_complete',completion_state('eos',10,512)=='COMPLETE')
    check('cap_termination_stays_incomplete',completion_state('length',512,512)=='INCOMPLETE_OUTPUT_CAP')
    check('at_cap_natural_eos_conservative',completion_state('eos',512,512)=='INCOMPLETE_OUTPUT_CAP')
    check('no_historical_sse_collector_import',all('StreamMeasure' not in (Path(__file__).parent/f).read_text() for f in ('adapter_a.py','adapter_b.py')))
    for s in sanity_panel():
        check(s['case_id']+'_reference',sanity_verdict(s['name'],s['expected_text'])['status']=='PASS')
    # Deliberate container-only runaway; checks enforced CPU limit, not host exec.
    runaway=sandbox({'code':'def spin():\n    while True:\n        pass\n','function':'spin','tests':[{'args':[],'expected':0}]})
    check('isolated_runaway_rejected',runaway.get('status')=='FAIL_CODE_TEST',runaway)
    blocked=sandbox({'code':'import os\ndef f(): return 1\n','function':'f','tests':[{'args':[],'expected':1}]})
    check('forbidden_import_rejected',blocked.get('status')=='FAIL_CODE_TEST',blocked)
    import dataclasses
    from common import plain
    @dataclasses.dataclass
    class MockCompletion:
        text: str
        token_ids: list
        finish_reason: str
    class MockOutput:
        def __init__(self):
            self.prompt_token_ids=[1,2]
            self.outputs=[MockCompletion('323',[5,6,7],'stop')]
            self.finished=True
            self.num_cached_tokens=0
            self.metrics=None
    native=plain(MockOutput())
    check('native_output_serialization',native['outputs'][0]['token_ids']==[5,6,7] and native['finished'] is True)
    check('native_json_no_loss',json.loads(json.dumps(native,allow_nan=False))==native)
    from evaluate import selftest as paired_selftest
    paired_selftest()
    check('paired_evaluator_preserves_all_denominators',True)
    if a.root:
        rendered=read_jsonl(a.root/'cases.jsonl');sani=read_jsonl(a.root/'sanity.jsonl')
        check('rendered_case_order', [x['case_id'] for x in rendered]==[x['case_id'] for x in cases])
        for c in rendered+sani:
            check(c['case_id']+'_input_budget',0<len(c['input_token_ids'])<=2048 and len(c['input_token_ids'])+c['output_cap']+32<=4096)
            check(c['case_id']+'_token_id_hash',ids_sha(c['input_token_ids'])==c['input_token_ids_sha256'])
            check(c['case_id']+'_thinking_template',c['rendered_text'].endswith('<think></think>') and c['thinking'] is False)
        if (a.root/'source-SHA256SUMS').exists():check('frozen_files',verify_freeze(a.root)['status']=='PASS')
    report={'schema':'mimo26-quality-cpu-tests-v1','status':'PASS','checks_passed':len(checks),
            'checks':checks,'new_gpu_calls':0,'code_execution':'ONLY_EXISTING_ROOTLESS_PODMAN_SANDBOX'}
    if a.receipt:atomic(a.receipt,report)
    print(json.dumps({'status':'CPU_TEST_PASS','checks':len(checks),'cases':24,'sandbox':'PASS','new_gpu_calls':0}))

if __name__=='__main__':main()
