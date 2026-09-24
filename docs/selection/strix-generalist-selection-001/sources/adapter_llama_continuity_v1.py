"""Q/M nonstreaming native-token collector, adapted from qualified MiMo001/002."""
from __future__ import annotations
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request
from common import atomic,base_record,begin_request,completion_state,error_record,now,persist_result,read_jsonl,sha,snapshot,split_reasoning,verify_freeze
from validate import sanity_verdict
from mtp_process_v1 import verify_addendum, collect_off


def http(base,path,payload=None,timeout=10):
    req=urllib.request.Request(base+path,data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Content-Type':'application/json'} if payload is not None else {},method='POST' if payload is not None else 'GET')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req,timeout=timeout) as response:return json.loads(response.read(33554432))


def main():
    root=Path(os.environ['GS_ROOT']).resolve();run=Path(os.environ['GS_RUN_DIR']);profile=os.environ['GS_PROFILE']
    if profile not in ('Q','M'):raise ValueError('invalid llama profile')
    verify_addendum(root)
    frozen=verify_freeze(root);manifest=json.loads((root/'source-manifest.json').read_text());cfg=manifest['profiles'][profile]
    assert sha(cfg['binary']['path'])==cfg['binary']['sha256'],'BINARY_PIN_MISMATCH'
    for path,value in cfg['library_hashes'].items():assert sha(path)==value,'LIBRARY_PIN_MISMATCH:'+path
    if (run/'arm-result.json').exists():raise RuntimeError('RUN_ALREADY_COMPLETED')
    from tokenizers import Tokenizer
    tokenizer=Tokenizer.from_file(str(root/cfg['tokenizer_json']))
    requests=read_jsonl(root/('requests-'+profile+'.jsonl'))
    base='http://127.0.0.1:'+str(cfg['port']);proc=None;log=None;phase='load'
    before=snapshot();started=time.monotonic()
    atomic(run/'load.json',{'status':'IN_PROGRESS','started_at':now(),'memory_before':before,'source_freeze':frozen})
    atomic(run/'quality.json',{'status':'NOT_EVALUATED'})
    def stop():
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=60)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=15)
    def interrupted(sig,frame):
        atomic(run/'fatal.json',{'phase':phase,'status':'INTERRUPTED','signal':sig,'at':now()});stop();raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    sanity={'preflight':[],'postflight':[]};completed=[]
    try:
        log=(run/'server.log').open('x');proc=subprocess.Popen(cfg['command'],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'LLAMA_TRACE':'1'})
        deadline=time.monotonic()+cfg['load_timeout_s']
        while time.monotonic()<deadline:
            if proc.poll() is not None:raise RuntimeError('SERVER_EXIT_DURING_LOAD:'+str(proc.returncode))
            try:
                if http(base,'/health',timeout=2).get('status')=='ok':break
            except Exception:pass
            time.sleep(1)
        else:raise TimeoutError('LOAD_HEALTH_DEADLINE')
        load_s=time.monotonic()-started
        after_load=snapshot(proc.pid)
        if after_load['memory_bytes']['MemAvailable']<cfg['minimum_memavailable_bytes']:
            raise RuntimeError('POST_LOAD_HEADROOM_GATE')
        checks={}
        for case in requests:
            key=case['input_ids_sha256']
            if key in checks:continue
            got=http(base,'/tokenize',{'content':case['rendered_text'],'add_special':False,'parse_special':True},timeout=60)['tokens']
            checks[key]={'actual_token_ids':got,'match':got==case['input_token_ids']}
            if got!=case['input_token_ids']:raise RuntimeError('RUNTIME_TOKENIZER_MISMATCH:'+case['request_key'])
        atomic(run/'input-checks.json',checks)
        props=http(base,'/props',timeout=10);atomic(run/'native-props.json',props)
        atomic(run/'load.json',{'status':'PASS','load_s':load_s,'pid':proc.pid,'finished_at':now(),'command':cfg['command'],
            'binary':cfg['binary'],'source_freeze':frozen,'memory_before':before,'memory_after':snapshot(proc.pid),'runtime_props':'native-props.json'})
        for case in requests:
            phase=case['phase']
            if phase=='panel' and len(sanity['preflight'])==6 and not all(x['status']=='PASS' for x in sanity['preflight']):raise RuntimeError('SANITY_PREFLIGHT_FAIL')
            request_id,dest=begin_request(root,run,case,profile,0,phase)
            record=base_record(root,run,case,profile,0,phase,request_id)
            s=case['sampling']
            payload={'prompt':case['input_token_ids'],'n_predict':case['output_cap'],'stream':False,'return_tokens':True,'return_progress':False,
                'temperature':s['temperature'],'top_k':s['top_k'],'top_p':s['top_p'],'min_p':s['min_p'],'seed':s['seed'],
                'repeat_penalty':s['repetition_penalty'],'presence_penalty':s['presence_penalty'],'frequency_penalty':s['frequency_penalty'],
                'dry_multiplier':0.0,'xtc_probability':0.0,'typical_p':1.0,'ignore_eos':False,'cache_prompt':False,
                'samplers':['penalties','top_k','top_p','min_p','temperature'],'backend_sampling':False}
            atomic(dest/'request.json',{'interface':'native /completion NONSTREAMING','payload':payload},exclusive=True)
            before_req=snapshot(proc.pid);t=time.perf_counter()
            try:
                raw=http(base,'/completion',payload,case['timeout_s']);elapsed=time.perf_counter()-t
                atomic(dest/'native-response.json',raw,exclusive=True);record['native_response']=raw
                if type(raw) is not dict or raw.get('stop') is not True:raise RuntimeError('MISSING_NATIVE_TERMINAL')
                ids=raw.get('tokens');n=raw.get('tokens_predicted');timings=raw.get('timings',{});finish=raw.get('stop_type')
                if type(ids) is not list or type(n) is not int or len(ids)!=n or timings.get('predicted_n')!=n:raise RuntimeError('NATIVE_OUTPUT_COUNT_MISMATCH')
                cache=timings.get('cache_n');native_n=timings.get('prompt_n')
                if cache!=0 or native_n!=len(case['input_token_ids']) or raw.get('tokens_evaluated')!=len(case['input_token_ids']):raise RuntimeError('PREFILL_IDENTITY_OR_REUSE_FAILURE')
                split=split_reasoning(raw.get('content',''),ids,case['thinking'],cfg,tokenizer)
                status=completion_state(finish,n,case['output_cap'],split['final_text'],phase)
                engine={'native':timings,'prompt_engine_s':timings.get('prompt_ms',0)/1000,'prompt_engine_tps':timings.get('prompt_per_second'),
                    'decode_engine_tps':timings.get('predicted_per_second'),'decode_contract':'native n_gen_steps=(n_gen-1); native prompt timing includes first-token sampling',
                    'first_generated_token_s':None,'first_final_token_s':None,'client_ttft_s':None}
                record.update(native_response=raw,native_input_ids_echoed=None,input_validation='FROZEN_IDS_AND_NATIVE_TOKENIZER_MATCH',
                    output_token_ids=ids,output_tokens=n,finish_reason=finish,completion_status=status,cache_reused_tokens=cache,cache_gate_pass=True,native_prompt_processed=native_n,
                    request_latency_s=elapsed,observer='HTTP caller: submit to complete nonstreaming response read',t_submit=t,t_done=t+elapsed,
                    engine_metrics=engine,resource_before=before_req,resource_after=snapshot(proc.pid),error=None,**split)
                record['final_chars']=len(record['final_text']);record['final_bytes']=len(record['final_text'].encode());record['reasoning_chars']=len(record['reasoning_text'])
                if elapsed>case['timeout_s']:record.update(completion_status='TIMEOUT',error='RETURN_AFTER_FROZEN_DEADLINE')
                persist_result(dest,record,run,0)
                if record['completion_status'] in ('TECHNICAL_ERROR','TIMEOUT','OVER_OUTPUT'):raise RuntimeError(record['error'] or record['completion_status'])
            except Exception as exc:
                if not (dest/'result.json').exists():persist_result(dest,error_record(record,exc,time.perf_counter()-t),run,0)
                raise
            completed.append({'request_id':request_id,'phase':phase,'case_id':case['case_id'],'completion_status':record['completion_status']})
            if phase in sanity:
                verdict=sanity_verdict(case['sanity_name'],record['final_text'],record['completion_status'])
                sanity[phase].append({'case_id':case['case_id'],**verdict})
                if len(sanity[phase])==6:
                    status='PASS' if all(x['status']=='PASS' for x in sanity[phase]) else 'FAIL'
                    atomic(run/('sanity-pre.json' if phase=='preflight' else 'sanity-post.json'),{'status':status,'phase':phase,'tests':sanity[phase],'at':now()})
                    if phase=='preflight':
                        atomic(run/'quality.json',{'status':'IN_PROGRESS' if status=='PASS' else 'FAIL','preflight':sanity[phase]})
                        if status!='PASS':raise RuntimeError('SANITY_PREFLIGHT_FAIL')
            atomic(run/'panel-progress.json',{'phase':phase,'records_completed':len(completed),'panel_completed':sum(x['phase']=='panel' for x in completed),'at':now()})
        quality='PASS' if all(x['status']=='PASS' for x in sanity['postflight']) and len(sanity['postflight'])==6 else 'FAIL'
        atomic(run/'quality.json',{'status':quality,'preflight':sanity['preflight'],'postflight':sanity['postflight'],'note':'Sanity/collection status, not task correctness'})
        atomic(run/'arm-result.json',{'profile':profile,'run_id':run.name,'source_freeze':frozen,'requests':completed,'sanity':sanity,'status':'COMPLETE','at':now()})
        if profile=='Q' and quality=='PASS':
            phase='mtp_off_after_primary_complete'
            try:collect_off(root,run,base,cfg,proc)
            except Exception as exc:
                atomic(run/'mtp-off-blocker.json',{'status':'BLOCKED','phase':phase,'error':type(exc).__name__+':'+str(exc),'primary_records_preserved':len(completed),'at':now()})
        return 0 if quality=='PASS' else 45
    except Exception as exc:
        atomic(run/'fatal.json',{'phase':phase,'status':'TECHNICAL_ERROR','error':type(exc).__name__+':'+str(exc),'at':now()});raise
    finally:
        stop()
        if log:log.close()

if __name__=='__main__':raise SystemExit(main())
