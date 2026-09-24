"""Existing E1 native TP2, HTTP nonstreaming; no kernel or release modifications."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import urllib.request
from common import atomic,base_record,begin_request,completion_state,error_record,now,persist_result,read_jsonl,sha,snapshot,verify_freeze
from validate import sanity_verdict


def http(base,path,payload=None,timeout=10):
    request=urllib.request.Request(base+path,data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,
        headers={'Content-Type':'application/json'} if payload is not None else {},method='POST' if payload is not None else 'GET')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request,timeout=timeout) as response:return json.loads(response.read(33554432))


def parse_trace(block,case,payload,sequence):
    marker='===== end request '+str(sequence)+' ====='
    if marker not in block:raise ValueError('native trace terminal missing')
    if block.count('===== request ')!=1:raise ValueError('native trace unexpected request cardinality')
    header=block.split('\n--- raw request json ---\n',1)[0]
    fields={}
    for line in header.splitlines():
        if ': ' in line:
            k,v=line.split(': ',1);fields[k]=v
    raw_request=block.split('\n--- raw request json ---\n',1)[1].split('\n--- rendered prompt ---\n',1)[0]
    if json.loads(raw_request)!=payload:raise ValueError('native request payload mismatch')
    rendered=block.split('\n--- rendered prompt ---\n',1)[1].split('\n--- generated text ---\n',1)[0]
    if rendered.endswith('\n') and not case['rendered_text'].endswith('\n'):rendered=rendered[:-1]
    if rendered!=case['rendered_text']:raise ValueError('native renderer mismatch')
    n=len(case['input_token_ids'])
    if any(int(fields[k])!=n for k in ['prompt_tokens','effective_prompt_tokens']):raise ValueError('native prompt token count mismatch')
    if int(fields['cached_tokens'])!=0 or int(fields['tools'])!=0 or int(fields['stream'])!=0:raise ValueError('native cache/tools/stream contract')
    if fields['think_mode']!=('max' if case['thinking'] else 'none'):raise ValueError('native thinking control mismatch')
    for key in ['temperature','top_p','min_p']:
        if float(fields[key])!=case['sampling'][key]:raise ValueError('native sampling '+key)
    if int(fields['top_k'])!=case['sampling']['top_k'] or int(fields['seed'])!=case['sampling']['seed']:raise ValueError('native sampling topk/seed')
    if int(fields['ignore_eos'])!=0 or int(fields['max_tokens'])!=case['output_cap']:raise ValueError('native EOS/cap contract')
    generated=block.split('\n--- generated text ---\n',1)[1].split('\n\n--- parsed message ---\n',1)[0]
    if 'tool-error continuation' in generated or 'repaired unterminated tool call' in generated:raise ValueError('unrequested semantic recovery')
    final_header=block.split('\n\n--- parsed message ---\n',1)[1].split('\n\n',1)[0]
    final={k:v for k,v in (line.split(': ',1) for line in final_header.splitlines() if ': ' in line)}
    return {'request_sequence':sequence,'header':fields,'finish':final.get('finish'),'generated_tokens':int(final['generated_tokens']),
            'engine_request_elapsed_s_rounded':float(final['elapsed_sec']),'rendered_match':True,'input_ids_note':'Exact trace rendering and count match tokens produced by the same pinned native CPU tokenizer; API does not echo the full ID list.'}


def rounded_engine_logs(text,input_tokens,output_tokens):
    prompt=None;decode=None
    for line in text.splitlines():
        p=re.search(r'prefill chunk (\d+)/(\d+) .*?avg=([\d.]+) t/s ([\d.]+)s',line)
        if p and int(p[1])==int(p[2])==input_tokens:
            prompt={'tokens':int(p[1]),'tps':float(p[3]),'seconds':float(p[4]),'line':line}
        d=re.search(r'gen=(\d+).*?decoding chunk=[\d.]+ t/s avg=([\d.]+) t/s ([\d.]+)s',line)
        if d and int(d[1])==output_tokens:decode={'tokens':int(d[1]),'tps':float(d[2]),'seconds':float(d[3]),'line':line}
    return {'prompt_engine_s':None if prompt is None else prompt['seconds'],'prompt_engine_tps':None if prompt is None else prompt['tps'],
            'decode_engine_tps':None,'decode_engine_total_rate_rounded':None if decode is None else decode['tps'],
            'native_log_prompt':prompt,'native_log_decode':decode,
            'precision':'Native log time rounded to 0.001 s; rates to 0.01 tok/s. Not reconstructed unrounded timestamps.',
            'decode_contract':'Native log completion/elapsed since decode_t0 (includes first token); NOT post-first-token rate.',
            'first_generated_token_s':None,'first_final_token_s':None,'client_ttft_s':None}


def peer_snapshot(root,cfg):
    cmd=['ssh','-o','IdentityAgent=none','-o','BatchMode=yes','-o','ConnectTimeout=5','02-evo-x3-tb',
         '/usr/bin/python3',str(Path(cfg['peer_root'])/'sources/resource_probe.py'),'--unit',cfg['peer_unit']]
    try:
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=12)
        return json.loads(cp.stdout) if cp.returncode==0 else {'status':'UNAVAILABLE','returncode':cp.returncode,'stderr':cp.stderr[:500]}
    except Exception as e:return {'status':'UNAVAILABLE','error':type(e).__name__+':'+str(e)}


def main():
    root=Path(os.environ['GS_ROOT']).resolve();run=Path(os.environ['GS_RUN_DIR']);profile='D'
    from d_readiness_recovery_v1 import ready_models,verify_recovery,effective_manifest
    recovery=verify_recovery(root)
    frozen=verify_freeze(root);manifest=effective_manifest(root,json.loads((root/'source-manifest.json').read_text()));cfg=manifest['profiles']['D']
    atomic(run/'recovery-source-receipt.json',recovery,exclusive=True)
    assert sha(cfg['binary']['path'])==cfg['binary']['sha256'],'E1_BINARY_CHANGED'
    assert Path(cfg['model_path']).stat().st_size==cfg['model_size'],'E1_MODEL_SIZE_CHANGED'
    requests=read_jsonl(root/'requests-D.jsonl');proc=None;log=None;phase='load';sanity={'preflight':[],'postflight':[]};completed=[]
    base='http://127.0.0.1:'+str(cfg['port']);trace=run/'server-trace.log'
    before=snapshot();start=time.monotonic()
    atomic(run/'load.json',{'status':'IN_PROGRESS','started_at':now(),'source_freeze':frozen,'memory_before':before})
    atomic(run/'quality.json',{'status':'NOT_EVALUATED'})
    def stop():
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=90)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=15)
    def interrupted(sig,frame):
        atomic(run/'fatal.json',{'phase':phase,'status':'INTERRUPTED','signal':sig,'at':now()});stop();raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        log=(run/'server.log').open('x');proc=subprocess.Popen(cfg['command'],stdout=log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+cfg['load_timeout_s']
        while time.monotonic()<deadline:
            if proc.poll() is not None:raise RuntimeError('E1_SERVER_EXIT_DURING_LOAD:'+str(proc.returncode))
            try:
                health=http(base,'/v1/models',timeout=2)
                if ready_models(health,cfg['api_model'],16384):break
            except Exception:pass
            time.sleep(1)
        else:raise TimeoutError('E1_LOAD_HEALTH_DEADLINE')
        models=http(base,'/v1/models',timeout=5);atomic(run/'native-models.json',models)
        atomic(run/'load.json',{'status':'PASS','load_s':time.monotonic()-start,'pid':proc.pid,'finished_at':now(),'command':cfg['command'],'binary':cfg['binary'],
            'source_freeze':frozen,'memory_before':before,'memory_after':snapshot(proc.pid),'peer_memory_after':peer_snapshot(root,cfg),
            'model_identity_note':'Identity comes from pinned E1 binary, DeepSeek-V4.1 GGUF metadata/size and matching peer; API display ID is recorded separately.'})
        checks={};sequence=0
        for case in requests:
            phase=case['phase'];sequence+=1
            request_id,dest=begin_request(root,run,case,profile,0,phase);record=base_record(root,run,case,profile,0,phase,request_id)
            s=case['sampling'];payload={'model':cfg['api_model'],'messages':case['messages'],'max_tokens':case['output_cap'],'stream':False,
                'reasoning_effort':'max' if case['thinking'] else 'none','thinking':case['thinking'],'temperature':s['temperature'],
                'top_k':s['top_k'],'top_p':s['top_p'],'min_p':s['min_p'],'seed':s['seed'],'ignore_eos':False,'tools':[],'tool_choice':'none'}
            atomic(dest/'request.json',{'interface':'E1 /v1/chat/completions NONSTREAMING','payload':payload},exclusive=True)
            log_offset=(run/'server.log').stat().st_size;trace_offset=trace.stat().st_size if trace.exists() else 0
            before_req=snapshot(proc.pid);peer_before=peer_snapshot(root,cfg);t=time.perf_counter()
            try:
                raw=http(base,'/v1/chat/completions',payload,case['timeout_s']);elapsed=time.perf_counter()-t
                atomic(dest/'native-response.json',raw,exclusive=True);record['native_response']=raw
                if len(raw.get('choices',[]))!=1:raise RuntimeError('NATIVE_RESPONSE_CARDINALITY')
                choice=raw['choices'][0];msg=choice.get('message',{});final=msg.get('content') or '';reason=msg.get('reasoning_content') or ''
                if type(final) is not str or type(reason) is not str:raise RuntimeError('NATIVE_CONTENT_TYPE')
                if msg.get('tool_calls'):raise RuntimeError('UNREQUESTED_TOOL_CALL_OUTPUT')
                usage=raw.get('usage',{});n=usage.get('completion_tokens');cache=(usage.get('prompt_tokens_details') or {}).get('cached_tokens')
                if type(n) is not int or usage.get('prompt_tokens')!=len(case['input_token_ids']) or cache!=0:raise RuntimeError('NATIVE_USAGE_OR_CACHE_CONTRACT')
                end_marker='===== end request '+str(sequence)+' =====';block=''
                for _ in range(30):
                    if trace.exists():
                        with trace.open('rb') as f:f.seek(trace_offset);block=f.read().decode()
                    if end_marker in block:break
                    time.sleep(.1)
                audit=parse_trace(block,case,payload,sequence);(dest/'native-trace.txt').write_text(block)
                if audit['generated_tokens']!=n or audit['finish']!=choice.get('finish_reason'):raise RuntimeError('NATIVE_TRACE_USAGE_FINISH_MISMATCH')
                checks[case['request_key']+':'+phase]=audit
                atomic(run/'input-checks.json',checks)
                with (run/'server.log').open('rb') as f:f.seek(log_offset);segment=f.read().decode(errors='replace')
                (dest/'native-log.txt').write_text(segment)
                engine=rounded_engine_logs(segment,len(case['input_token_ids']),n)
                status=completion_state(choice.get('finish_reason'),n,case['output_cap'],final,phase)
                record.update(native_response=raw,native_input_ids_echoed=None,input_validation='NATIVE_TRACE_RENDER_COUNT_AND_SAME_BINARY_CPU_TOKENIZATION',
                    output_token_ids=None,output_tokens=n,finish_reason=choice.get('finish_reason'),completion_status=status,
                    cache_reused_tokens=cache,cache_gate_pass=True,native_prompt_processed=len(case['input_token_ids']),
                    final_text=final,reasoning_text=reason,reasoning_observed=bool(reason),reasoning_closed=bool(final) or not case['thinking'],
                    reasoning_tokens_native=None,final_tokens_native=None,boundary_method='native separate message.content/reasoning_content; no retokenized native-ID claim',
                    request_latency_s=elapsed,observer='HTTP caller: submit to complete nonstreaming response read',t_submit=t,t_done=t+elapsed,
                    engine_metrics=engine,native_trace_audit=audit,resource_before=before_req,resource_after=snapshot(proc.pid),peer_resource_before=peer_before,peer_resource_after=peer_snapshot(root,cfg),error=None)
                record['final_chars']=len(final);record['final_bytes']=len(final.encode());record['reasoning_chars']=len(reason)
                if elapsed>case['timeout_s']:record.update(completion_status='TIMEOUT',error='RETURN_AFTER_FROZEN_DEADLINE')
                persist_result(dest,record,run,0)
                if record['completion_status'] in ('TECHNICAL_ERROR','TIMEOUT','OVER_OUTPUT'):raise RuntimeError(record['error'] or record['completion_status'])
            except Exception as exc:
                if not (dest/'result.json').exists():persist_result(dest,error_record(record,exc,time.perf_counter()-t),run,0)
                raise
            completed.append({'request_id':request_id,'phase':phase,'case_id':case['case_id'],'completion_status':record['completion_status']})
            if phase in sanity:
                v=sanity_verdict(case['sanity_name'],final,record['completion_status']);sanity[phase].append({'case_id':case['case_id'],**v})
                if len(sanity[phase])==6:
                    status='PASS' if all(x['status']=='PASS' for x in sanity[phase]) else 'FAIL'
                    atomic(run/('sanity-pre.json' if phase=='preflight' else 'sanity-post.json'),{'phase':phase,'status':status,'tests':sanity[phase],'at':now()})
                    if phase=='preflight':
                        atomic(run/'quality.json',{'status':'IN_PROGRESS' if status=='PASS' else 'FAIL','preflight':sanity[phase]})
                        if status!='PASS':raise RuntimeError('SANITY_PREFLIGHT_FAIL')
            atomic(run/'panel-progress.json',{'phase':phase,'records_completed':len(completed),'panel_completed':sum(x['phase']=='panel' for x in completed),'at':now()})
        quality='PASS' if len(sanity['postflight'])==6 and all(x['status']=='PASS' for x in sanity['postflight']) else 'FAIL'
        atomic(run/'quality.json',{'status':quality,'preflight':sanity['preflight'],'postflight':sanity['postflight'],'note':'Technical collection/sanity, not task quality'})
        atomic(run/'arm-result.json',{'profile':'D','run_id':run.name,'requests':completed,'sanity':sanity,'source_freeze':frozen,'status':'COMPLETE','at':now()})
        return 0 if quality=='PASS' else 45
    except Exception as exc:
        atomic(run/'fatal.json',{'phase':phase,'status':'TECHNICAL_ERROR','error':type(exc).__name__+':'+str(exc),'at':now()});raise
    finally:
        stop()
        if log:log.close()

if __name__=='__main__':raise SystemExit(main())
