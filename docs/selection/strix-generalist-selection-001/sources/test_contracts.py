"""CPU-only adapter/lifecycle counterexamples; every process transition is mocked."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from adapter_ds41 import parse_trace,rounded_engine_logs
from common import atomic,base_record,digest,ids_sha,split_reasoning
from evaluate import record_audit,stats
from window_guards import validate_resident
from window_runner import terminal_decision
import window_cleanup


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();checks=[]
    def ck(name,value):
        if not value:raise AssertionError(name)
        checks.append({'name':name,'pass':True})
    def reject(name,func):
        try:func()
        except (ValueError,RuntimeError,AssertionError):ck(name,True);return
        raise AssertionError(name+' was accepted')
    st={'state':'READY','preset':'dspark-k2-gfx1151','release_id':'5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513','owner':'DS41','owner_state':'RUNNING','epoch':'42','paired_backend_http':'200',
        'ranks':[{'rank':0,'active':True,'health_http':'200'},{'rank':1,'active':True,'health_http':'200'}]}
    owner={'owner':'DS41','state':'RUNNING','epoch':'42','ranks':{'0':{'invocation_id':'a'},'1':{'invocation_id':'b'}}}
    units={'0':{'ActiveState':'active','MainPID':'10','InvocationID':'a'},'1':{'ActiveState':'active','MainPID':'11','InvocationID':'b'}}
    health={'status':'ok','busy':False,'poison':''}
    ck('admission_expected_resident',validate_resident(st,owner,units,health))
    for field,value in [('owner','OTHER'),('epoch','41'),('state','OFF')]:
        bad=copy.deepcopy(owner);bad[field]=value
        reject('owner_guard_'+field,lambda:validate_resident(st,bad,units,health))
    bad=copy.deepcopy(units);bad['1']['InvocationID']='foreign'
    reject('foreign_peer_invocation',lambda:validate_resident(st,owner,bad,health))
    reject('busy_resident',lambda:validate_resident(st,owner,units,{**health,'busy':True}))
    bad=copy.deepcopy(st);bad['ranks'][1]['health_http']='000'
    reject('unknown_peer_health',lambda:validate_resident(bad,owner,units,health))
    done={'ActiveState':'inactive','Result':'success','ExecMainStatus':'0'};running={'ActiveState':'active','Result':'success','ExecMainStatus':'0'}
    bad={'ActiveState':'failed','Result':'exit-code','ExecMainStatus':'7'}
    ck('one_rank_done_does_not_finish',terminal_decision(done,running,True)=='WAIT')
    ck('both_rank_done_finishes',terminal_decision(done,done,True)=='COMPLETE')
    ck('single_rank_done_finishes',terminal_decision(done,{},False)=='COMPLETE')
    ck('peer_failure_stops',terminal_decision(running,bad,True)=='FAIL')
    ck('rank0_failure_stops',terminal_decision(bad,running,True)=='FAIL')
    case={'rendered_text':'<BOS>prompt<ASSISTANT><think>','input_token_ids':[5,6,7],'thinking':True,'output_cap':4096,
          'sampling':{'temperature':1.0,'top_p':.95,'min_p':0.0,'top_k':0,'seed':101}}
    payload={'messages':[{'role':'user','content':'prompt'}],'max_tokens':4096,'stream':False}
    header='\n'.join(['===== request 1 time =====','kind: chat','stream: 0','tools: 0','think_mode: max','prompt_tokens: 3','effective_prompt_tokens: 3','cached_tokens: 0','max_tokens: 4096','temperature: 1.000','top_k: 0','top_p: 0.950','min_p: 0.000','ignore_eos: 0','seed: 101'])
    trace=header+'\n--- raw request json ---\n'+json.dumps(payload)+'\n--- rendered prompt ---\n'+case['rendered_text']+'\n--- generated text ---\nreason</think>{}\n\n--- parsed message ---\nfinish: stop\ngenerated_tokens: 7\nelapsed_sec: 0.500\n\nreasoning: reason\ncontent: {}\n===== end request 1 =====\n'
    result=parse_trace(trace,case,payload,1);ck('native_D_trace_accepts_exact',result['generated_tokens']==7 and result['rendered_match'])
    for field,old,new in [('cache','cached_tokens: 0','cached_tokens: 1'),('thinking','think_mode: max','think_mode: high'),('tools','tools: 0','tools: 1'),('sampling','top_p: 0.950','top_p: 0.900'),('prompt','effective_prompt_tokens: 3','effective_prompt_tokens: 2')]:
        reject('native_D_trace_'+field,lambda old=old,new=new:parse_trace(trace.replace(old,new),case,payload,1))
    reject('native_D_raw_payload',lambda:parse_trace(trace,case,{'other':True},1))
    reject('native_D_renderer_disagreement',lambda:parse_trace(trace,{**case,'rendered_text':'other'},payload,1))
    reject('native_D_missing_terminal',lambda:parse_trace(trace.replace('===== end request 1 =====',''),case,payload,1))
    text='[s] prefill chunk 3/3 (100%) chunk=9.00 t/s avg=6.00 t/s 0.500s\n[s] gen=7 decoding chunk=9.00 t/s avg=3.50 t/s 2.000s\n'
    metric=rounded_engine_logs(text,3,7)
    ck('D_native_rounded_metric_contract',metric['prompt_engine_tps']==6 and metric['decode_engine_tps'] is None and metric['decode_engine_total_rate_rounded']==3.5 and metric['client_ttft_s'] is None)
    ck('D_incomplete_native_metric_not_filled',rounded_engine_logs(text,4,8)['prompt_engine_tps'] is None)
    q={'thinking_prefix_open':True,'think_open_id':10,'think_close_id':11,'eos_ids':[12]}
    class Decoder:
        def decode(self,ids,skip_special_tokens=False):return ''.join({0:'zero',1:'r',2:'{}',10:'<think>',11:'</think>',12:'<eos>'}[i] for i in ids)
    result=split_reasoning('r</think>{}',[0,1,11,2,12],True,q,Decoder())
    ck('native_decoding_preserves_zero_and_excludes_EOS',result['reasoning_text']=='zeror' and result['final_text']=='{}' and result['reasoning_tokens_native']==2 and result['final_tokens_native']==1)
    result=split_reasoning('{}',[2,12],True,{**q,'thinking_prefix_open':False},Decoder())
    ck('M_direct_final_not_repaired_into_reasoning',result['final_text']=='{}' and result['reasoning_observed'] is False)
    with tempfile.TemporaryDirectory(prefix='gs001-contract-') as tmp:
        root=Path(tmp);run=root/'run';run.mkdir();(root/'source-SHA256SUMS').write_text('')
        plan={'case_id':'c','request_key':'c','phase':'panel','profile':'Q','messages':[{'role':'user','content':'x'}],'rendered_text':'x','input_token_ids':[5],
              'input_ids_sha256':ids_sha([5]),'output_cap':4096,'thinking':True,'sampling':case['sampling'],'timeout_s':10}
        rec=base_record(root,run,plan,'Q',0,'panel','run/Q/panel/c')
        native={'tokens':[1,11,2,12],'tokens_predicted':4,'stop':True,'stop_type':'eos','timings':{'cache_n':0,'prompt_n':1,'predicted_n':4}}
        rec.update(native_response=native,output_token_ids=native['tokens'],output_tokens=4,finish_reason='eos',completion_status='COMPLETE',cache_reused_tokens=0,cache_gate_pass=True,native_prompt_processed=1,final_text='{}',request_latency_s=1)
        rec['record_sha256']=digest(rec);dest=run/'requests/panel__c/result.json';atomic(dest,rec)
        ck('raw_record_native_consistency',record_audit(root,run,'Q',plan,rec)==[])
        damaged=copy.deepcopy(rec);damaged['output_tokens']=5;damaged['record_sha256']=digest({k:v for k,v in damaged.items() if k!='record_sha256'});atomic(dest,damaged)
        ck('raw_output_count_mutation_rejected',bool(record_audit(root,run,'Q',plan,damaged)))
        untouched={'campaign':'STRIX-GENERALIST-SELECTION-001','rank0':None,'rank1':None}
        atomic(run/'config.json',untouched);atomic(run/'result.json',{'run_completion':'BLOCKED','initial_cause':'admission'})
        (run/'events.jsonl').write_text('')
        with patch.object(window_cleanup,'LOCK',root/'cleanup.lock'),patch.object(window_cleanup,'controller_status',return_value=st),patch.object(window_cleanup.subprocess,'run') as call:
            result=window_cleanup.cleanup(run)
            ck('blocked_admission_does_not_transition_resident',result['status']=='PASS' and call.call_count==0)
            ck('cleanup_preserves_initial_failure',json.loads((run/'result.json').read_text())['initial_cause']=='admission')
    ck('empty_stats_null',stats([])['median'] is None)
    ck('median_not_best_of',stats([1,8,9])['median']==8)
    atomic(a.output,{'status':'PASS','checks':checks,'new_model_calls':0,'lifecycle_transitions':'MOCKED_ONLY'})
    print(json.dumps({'status':'ADAPTER_LIFECYCLE_CPU_PASS','checks':len(checks),'new_model_calls':0}))

if __name__=='__main__':main()
