"""New frozen A collector: native /completion NONSTREAMING, one model load."""
from __future__ import annotations
import json
import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path
from common import (atomic,base_result,begin_request,completion_state,failure_record,now,
                    persist_result,read_jsonl,sha,snapshot,verify_freeze)
from validate import sanity_verdict


def http(base,path,payload=None,timeout=10):
    request=urllib.request.Request(base+path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Content-Type':'application/json'} if payload is not None else {},
        method='POST' if payload is not None else 'GET')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request,timeout=timeout) as response:
        return json.loads(response.read(16777216))


def main():
    root=Path(os.environ['QR_ROOT']);run=Path(os.environ['QR_RUN_DIR'])
    arm='A';rank=0
    frozen=verify_freeze(root)
    manifest=json.loads((root/'source-manifest.json').read_text())
    cfg=manifest['runtimes']['A'];binary=cfg['binary']
    if sha(binary['path'])!=binary['sha256']:raise RuntimeError('A_BINARY_PIN_MISMATCH')
    if (run/'arm-result.json').exists():raise RuntimeError('RUN_ALREADY_HAS_RESULT')
    cases=read_jsonl(root/'cases.jsonl');sanity=read_jsonl(root/'sanity.jsonl')
    base='http://127.0.0.1:'+str(cfg['port'])
    proc=None;log=None;phase='load';load_start=time.monotonic()
    atomic(run/'load.json',{'status':'IN_PROGRESS','started_at':now(),'memory_before':snapshot(),'source_freeze':frozen})
    atomic(run/'quality.json',{'status':'NOT_EVALUATED'})
    before=snapshot()
    def stop():
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=40)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=10)
    def interrupted(sig,frame):
        atomic(run/'fatal.json',{'status':'INTERRUPTED','phase':phase,'signal':sig,'at':now()})
        stop();raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def generate(case,phase):
        request_id,dest=begin_request(run,case,arm,rank,phase,root)
        result=base_result(run,case,arm,rank,phase,request_id,root)
        result['runtime']={'name':'llama.cpp','commit':cfg['runtime_commit'],'binary_sha256':binary['sha256']}
        payload={'prompt':case['input_token_ids'],'n_predict':case['output_cap'],'stream':False,
            'temperature':0.0,'seed':1,'top_k':0,'top_p':1.0,'min_p':0.0,
            'repeat_penalty':1.0,'presence_penalty':0.0,'frequency_penalty':0.0,
            'dry_multiplier':0.0,'xtc_probability':0.0,'ignore_eos':False,'cache_prompt':False,
            'return_tokens':True,'return_progress':False}
        result['request_payload']=payload
        atomic(dest/'request.json',{'endpoint':'/completion','payload':payload},exclusive=True)
        before_req=snapshot(proc.pid);start=time.perf_counter()
        try:
            raw=http(base,'/completion',payload,case['timeout_s'])
            elapsed=time.perf_counter()-start
            if not isinstance(raw,dict) or 'content' not in raw or raw.get('stop') is not True:
                raise RuntimeError('MISSING_NONSTREAM_TERMINAL_RESULT')
            timings=raw.get('timings') or {};count=raw.get('tokens_predicted');ids=raw.get('tokens')
            finish=raw.get('stop_type');status=completion_state(finish,count,case['output_cap'])
            cache_ok=(timings.get('cache_n')==0 and timings.get('prompt_n')==len(case['input_token_ids']) and raw.get('tokens_evaluated')==len(case['input_token_ids']))
            collector_ok=isinstance(ids,list) and type(count) is int and len(ids)==count and timings.get('predicted_n')==count
            result.update(native_response=raw,final_text=raw['content'],output_tokens=count,output_token_ids=ids,
                native_output_ids_available=isinstance(ids,list),native_input_ids_echoed=None,
                input_validation='DIRECT_FROZEN_IDS_AND_RUNTIME_TOKENIZER_MATCH',finish_reason=finish,
                completion_status=status,cache_reused_tokens=timings.get('cache_n'),cache_gate_pass=cache_ok,
                native_prompt_processed=timings.get('prompt_n'),native_context_tokens_cached=raw.get('tokens_cached'),
                diagnostic_wall_s=elapsed,diagnostic_clock='perf_counter in A HTTP caller, complete response read',
                t_submit_monotonic=start,t_done_monotonic=start+elapsed,resource_before=before_req,
                resource_after=snapshot(proc.pid),collector_consistency_pass=collector_ok,error=None)
            if not cache_ok or not collector_ok or status=='TECHNICAL_ERROR':
                result['completion_status']='TECHNICAL_ERROR';result['error']='CACHE_OR_NATIVE_CONTRACT_FAILURE'
            if elapsed>case['timeout_s']:
                result['completion_status']='TIMEOUT';result['error']='COMPLETION_AFTER_PREREGISTERED_DEADLINE'
            persist_result(dest,result,run,rank)
            if result['completion_status'] in ('TECHNICAL_ERROR','TIMEOUT'):raise RuntimeError(result['error'])
            return result
        except Exception as e:
            if not (dest/'result.json').exists():persist_result(dest,failure_record(result,e),run,rank)
            raise
    def sanity_phase(phase):
        results=[]
        for case in sanity:
            response=generate(case,phase)
            value=sanity_verdict(case['name'],response['final_text'],response['completion_status'])
            results.append({'case_id':case['case_id'],'request_id':response['request_id'],**value})
        report={'phase':phase,'status':'PASS' if all(x['status']=='PASS' for x in results) else 'FAIL','tests':results,'at':now()}
        atomic(run/('sanity-pre.json' if phase=='preflight' else 'sanity-post.json'),report)
        return report
    try:
        log=(run/'server.log').open('x')
        proc=subprocess.Popen(cfg['command'],stdout=log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+cfg['load_timeout_s']
        while time.monotonic()<deadline:
            if proc.poll() is not None:raise RuntimeError('SERVER_EXIT_DURING_LOAD:'+str(proc.returncode))
            try:
                if http(base,'/health',timeout=2).get('status')=='ok':break
            except Exception:pass
            time.sleep(1)
        else:raise TimeoutError('A_LOAD_HEALTH_TIMEOUT')
        load_s=time.monotonic()-load_start
        checks={}
        for case in sanity+cases:
            out=http(base,'/tokenize',{'content':case['rendered_text'],'add_special':False,'parse_special':True},timeout=60)
            got=[int(x) for x in out['tokens']]
            checks[case['case_id']]={'match':got==case['input_token_ids'],'actual_token_ids':got,'count':len(got)}
            if got!=case['input_token_ids']:raise RuntimeError('A_TOKENIZER_MISMATCH:'+case['case_id'])
        atomic(run/'input-checks.json',checks)
        atomic(run/'load.json',{'status':'PASS','load_s':load_s,'finished_at':now(),'pid':proc.pid,
            'runtime_commit':cfg['runtime_commit'],'binary_sha256':binary['sha256'],'command':cfg['command'],
            'memory_before':before,'memory_after':snapshot(proc.pid),'source_freeze':frozen,'input_checks':'input-checks.json'})
        phase='preflight';pre=sanity_phase(phase)
        if pre['status']!='PASS':
            atomic(run/'quality.json',{'status':'FAIL','preflight':pre,'postflight':None});raise RuntimeError('SANITY_PREFLIGHT_FAIL')
        atomic(run/'quality.json',{'status':'IN_PROGRESS','preflight':pre,'postflight':None})
        phase='panel';panel=[]
        for case in cases:
            rec=generate(case,phase);panel.append({'case_id':case['case_id'],'request_id':rec['request_id'],'completion_status':rec['completion_status'],'output_tokens':rec['output_tokens']})
            atomic(run/'panel-progress.json',{'status':'IN_PROGRESS','completed':len(panel),'planned':len(cases),'last_case':case['case_id'],'at':now()})
        phase='postflight';post=sanity_phase(phase)
        quality={'status':'PASS' if post['status']=='PASS' else 'FAIL','preflight':pre,'postflight':post,'panel_completions':len(panel),
                 'note':'PASS denotes sanity and collection, not independent panel verdicts'}
        atomic(run/'quality.json',quality)
        atomic(run/'arm-result.json',{'schema':'mimo26-quality-arm-v1','arm':arm,'run_id':run.name,'panel':panel,'sanity_pre':pre,'sanity_post':post,'source_freeze':frozen,'at':now()})
        atomic(run/'panel-progress.json',{'status':'COMPLETE','completed':len(panel),'planned':len(cases),'at':now()})
        return 0 if quality['status']=='PASS' else 45
    except Exception as e:
        atomic(run/'fatal.json',{'status':'TECHNICAL_ERROR','phase':phase,'error':type(e).__name__+':'+str(e),'at':now()})
        raise
    finally:
        stop()
        if log:log.close()

if __name__=='__main__':raise SystemExit(main())
