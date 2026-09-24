"""CPU-only tests of the additive MTP collector. All HTTP is fake."""
from pathlib import Path
import copy
import json
import sys
import tempfile
import hashlib

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
sys.path.insert(0,str(ROOT/'sources'))
import mtp_process_v1 as mtp
from common import ids_sha


def main():
    checks=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    sample={'case_id':'t','request_id':'off','output_token_ids':[7,8], 'native_response':{'content':'ok'},
            'finish_reason':'limit','input_token_ids':[1,2],'sampling':{'temperature':0},'cache_gate_pass':True}
    check('equal pair',mtp.compare_pair(sample,sample)['status']=='PASS')
    for label,field,value in [('tokens','output_token_ids',[7,9]),('text','native_response',{'content':'bad'}),('stop','finish_reason','eos'),
                              ('prompt','input_token_ids',[2,1]),('sampling','sampling',{'temperature':1}),('cache','cache_gate_pass',False)]:
        mutated=copy.deepcopy(sample);mutated[field]=value
        check('reject '+label,mtp.compare_pair(sample,mutated)['status']=='FAIL')
    mutated=copy.deepcopy(sample);mutated['output_token_ids']=[7]
    check('length mismatch index',mtp.compare_pair(sample,mutated)['first_different_token_index']==1)
    pairs=[{'status':'PASS'} for _ in range(6)]
    check('no state promotion from equal output',mtp.pair_gate(pairs,[{'draft_tokens':0}])['status']=='INCOMPLETE_STATE_BRANCH_NOT_EXERCISED')
    check('no guessed partial acceptance',mtp.pair_gate(pairs,[{'draft_tokens':4}])['status']=='INCOMPLETE_STATE_BRANCH_NOT_EXERCISED')
    check('full gate',mtp.pair_gate(pairs,[{'draft_tokens':4,'partial_acceptance_observed':True}])['status']=='PASS')
    check('failed pair stops gate',mtp.pair_gate([{'status':'FAIL'}]*6,[{'draft_tokens':4,'partial_acceptance_observed':True}])['status']=='FAIL')
    q=mtp.effective_cfg(ROOT,'OFF')['command'];b=mtp.effective_cfg(ROOT,'ON')['command']
    check('actual target only',q[q.index('--spec-type')+1]=='none' and '-md' not in q)
    check('actual draft process',b[b.index('--spec-type')+1]=='draft-mtp' and b[b.index('--spec-draft-n-max')+1]=='3')
    plans=json.loads((ROOT/'continuity/mtp-plan.json').read_text())
    check('bounded request counts',len(plans['OFF'])==len(plans['ON'])==12)
    check('bounded token budget',all(sum(x['output_cap'] for x in r)==2304 for r in plans.values()))
    check('paired full inputs',all(a['input_token_ids']==b['input_token_ids'] and a['sampling']==b['sampling'] for a,b in zip(plans['OFF'],plans['ON'])))
    check('beyond ubatch',any(x['input_tokens']>2048 for x in plans['OFF'][:6]))
    check('primary untouched',len([json.loads(x) for x in (ROOT/'requests-Q.jsonl').read_text().splitlines()])==32)
    original_methods={k:getattr(mtp,k) for k in ['verify_addendum','http','text_http','snapshot']}
    try:
        with tempfile.TemporaryDirectory(prefix='gs001-mtp-cpu-') as temp:
            root=Path(temp);(root/'continuity').mkdir();(root/'source-SHA256SUMS').write_text('fixture only\n')
            offrun=root/'primary';onrun=root/'extra';offrun.mkdir();onrun.mkdir()
            for p in [offrun,onrun]:(p/'server.log').write_text('')
            (root/'source-manifest.json').write_text(json.dumps({'runs':{'Q':{'run_dir':str(offrun)}}}))
            fixture={}
            for side in ['OFF','ON']:
                fixture[side]=[]
                for i in range(12):
                    phase='mtp_equivalence' if i<6 else 'mtp_benchmark';key=f'F{i}-{side}'
                    fixture[side].append({'case_id':f'F{i}','request_key':key,'phase':phase,'messages':[], 'rendered_text':'test',
                        'input_token_ids':[1,2],'input_ids_sha256':ids_sha([1,2]),'input_tokens':2,'thinking':False,
                        'output_cap':256 if i<6 else 128,'timeout_s':10,'sampling':plans[side][0]['sampling']})
            (root/'continuity/mtp-plan.json').write_text(json.dumps(fixture))
            state={'side':'OFF','completed':0,'run':offrun}
            mtp.verify_addendum=lambda root:{'status':'CPU_STUB_NO_MODEL','addendum_index_sha256':'fixture'}
            mtp.snapshot=lambda pid=None:{'CPU_STUB':True}
            def fake_http(base,path,payload=None,timeout=10):
                if path=='/props':return {'default_generation_settings':{'speculative':state['side']=='ON'}}
                if path=='/tokenize':return {'tokens':[1,2]}
                if path!='/completion':raise AssertionError('unplanned fake endpoint')
                check('no ignored toggle '+state['side']+str(state['completed']),not any('speculative' in k for k in payload))
                state['completed']+=1
                if state['side']=='ON':
                    with (state['run']/'server.log').open('a') as log:log.write('accepted 1/3 draft tokens\n')
                return {'tokens':[7,8],'tokens_predicted':2,'tokens_evaluated':2,'stop':True,'stop_type':'eos','content':'ok',
                        'timings':{'predicted_n':2,'prompt_n':2,'cache_n':0,'predicted_per_second':3.0}}
            mtp.http=fake_http
            mtp.text_http=lambda base,path:('llamacpp:spec_decode_num_draft_tokens_total '+str(3*state['completed'] if state['side']=='ON' else 0)+'\n'
                                      +'llamacpp:spec_decode_num_accepted_tokens_total '+str(state['completed'] if state['side']=='ON' else 0)+'\n')
            off=mtp.collect(root,offrun,'fake',{},0,'OFF');check('12 OFF persisted',off['records']==12)
            state.update(side='ON',completed=0,run=onrun)
            on=mtp.collect(root,onrun,'fake',{},0,'ON');check('ON full controlled gate',on['equivalence']['status']=='PASS' and on['records']==12)
            raw=onrun/'mtp-on/raw-results.jsonl';before=raw.read_bytes()
            try:mtp.collect(root,onrun,'fake',{},0,'ON')
            except FileExistsError:check('duplicate refused no overwritten results',raw.read_bytes()==before)
            else:raise AssertionError('duplicate accepted')
    finally:
        for k,v in original_methods.items():setattr(mtp,k,v)
    for line in (ROOT/'source-SHA256SUMS').read_text().splitlines():
        h,rel=line.split('  ',1);check('base unchanged '+rel,hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h)
    result={'status':'PASS','checks':len(checks),'checks_detail':checks,'new_inference_calls':0,'network_calls':0,'kind':'CPU mocked collector plus immutable-source checks'}
    (ROOT/'continuity/cpu-tests.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='checks_detail'}))

if __name__=='__main__':main()
