"""Append-only process-level MTP comparison. No per-request speculative toggle."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import urllib.request
from common import atomic, append, base_record, begin_request, completion_state, error_record, now, persist_result, sha, snapshot, split_reasoning, verify_freeze
from validate import sanity_verdict
from adapter_llama import http


def verify_addendum(root):
    root=Path(root).resolve()
    base=verify_freeze(root)
    manifest=json.loads((root/'continuity/addendum.json').read_text())
    if manifest['base_index_sha256']!=base['index_sha256']:raise RuntimeError('ADDENDUM_BASE_MISMATCH')
    index=root/'continuity/addendum-SHA256SUMS'
    for line in index.read_text().splitlines():
        h,rel=line.split('  ',1);p=(root/rel).resolve()
        if not p.is_relative_to(root) or sha(p)!=h:raise RuntimeError('ADDENDUM_BYTE_MISMATCH:'+rel)
    return {'status':'PASS','base':base,'addendum_index_sha256':sha(index)}


def text_http(base,path):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(base+path,timeout=10) as response:return response.read(4*1024*1024).decode()


def metrics(text):
    out={}
    for line in text.splitlines():
        if not line or line.startswith('#'):continue
        key,sep,val=line.partition(' ')
        if 'spec_decode_' in key or key.endswith(('tokens_predicted_total','n_decode_total')):
            out[key]=float(val.strip().split()[0])
    return out


def compare_pair(a,b):
    ids_a=a['output_token_ids'];ids_b=b['output_token_ids']
    mismatch=next((i for i,(x,y) in enumerate(zip(ids_a,ids_b)) if x!=y),None)
    if mismatch is None and len(ids_a)!=len(ids_b):mismatch=min(len(ids_a),len(ids_b))
    same=(ids_a==ids_b and a['native_response']['content']==b['native_response']['content']
          and a['finish_reason']==b['finish_reason'] and a['input_token_ids']==b['input_token_ids']
          and a['sampling']==b['sampling'] and a['cache_gate_pass'] and b['cache_gate_pass'])
    return {'case_id':a['case_id'],'status':'PASS' if same else 'FAIL','first_different_token_index':mismatch,
            'OFF_request_id':a['request_id'],'ON_request_id':b['request_id'],
            'OFF_tokens':len(ids_a),'ON_tokens':len(ids_b)}


def pair_gate(pairs,rows):
    exact=len(pairs)==6 and all(p['status']=='PASS' for p in pairs)
    active=any(r.get('draft_tokens',0)>0 for r in rows)
    partial=any(r.get('partial_acceptance_observed',False) for r in rows)
    status='PASS' if exact and active and partial else ('FAIL' if not exact else 'INCOMPLETE_STATE_BRANCH_NOT_EXERCISED')
    return {'status':status,'pairs':pairs,'drafting_observed':active,'partial_acceptance_observed':partial,'at':now()}


def effective_cfg(root,side):
    cfg=json.loads((root/'source-manifest.json').read_text())['profiles']['Q']
    cfg['command']=list(cfg['command'])
    if side=='ON':
        cfg['command'][cfg['command'].index('--spec-type')+1]='draft-mtp'
        cfg['command']+=['-md',str(Path(cfg['model_path']).parent/'mtp-Qwen3.8-Flash-Next-Q5_K-frspec-65k.gguf'),
            '--spec-draft-n-max','3','--spec-draft-p-min','0.0','--spec-draft-device','Vulkan0','-ngld','all']
    return cfg


def collect(root,run,base,cfg,pid,side):
    receipt=verify_addendum(root)
    subrun=run/('mtp-'+side.lower());subrun.mkdir(exist_ok=True)
    plan=json.loads((root/'continuity/mtp-plan.json').read_text())[side]
    props=http(base,'/props');atomic(subrun/'props.json',props,exclusive=True)
    settings=props.get('default_generation_settings',{})
    spec=settings.get('speculative')
    if spec is not (side=='ON'):raise RuntimeError('MTP_PROCESS_MODE_UNPROVEN:'+str(spec))
    rows=[];pairs=[];gate=None
    off_run=Path(json.loads((root/'source-manifest.json').read_text())['runs']['Q']['run_dir'])/'mtp-off'
    for case in plan:
        if side=='ON' and case['phase']=='mtp_benchmark':
            if gate is None:
                gate=pair_gate(pairs,rows)
                atomic(subrun/'equivalence.json',gate,exclusive=True)
            if gate['status']!='PASS':break
        key=case['request_key'];dest=subrun/'requests'/(case['phase']+'__'+key)
        rid,dest=begin_request(root,subrun,case,'Q-'+side,0,case['phase'])
        record=base_record(root,subrun,case,'Q-'+side,0,case['phase'],rid)
        record.update(parent_run_id=run.name,addendum=receipt,speculation=(side=='ON'))
        got=http(base,'/tokenize',{'content':case['rendered_text'],'add_special':False,'parse_special':True})['tokens']
        if got!=case['input_token_ids']:raise RuntimeError('MTP_INPUT_TOKENIZER_MISMATCH:'+key)
        s=case['sampling'];payload={'prompt':case['input_token_ids'],'n_predict':case['output_cap'],'stream':False,'return_tokens':True,'return_progress':False,
            'temperature':s['temperature'],'top_p':s['top_p'],'top_k':s['top_k'],'min_p':s['min_p'],'seed':s['seed'],
            'repeat_penalty':1.0,'presence_penalty':0.0,'frequency_penalty':0.0,'dry_multiplier':0.0,'xtc_probability':0.0,
            'typical_p':1.0,'ignore_eos':False,'cache_prompt':False,'backend_sampling':False,
            'samplers':['penalties','top_k','top_p','min_p','temperature']}
        atomic(dest/'request.json',{'endpoint':'/completion','payload':payload,'process_speculation':side},exclusive=True)
        before_metrics=text_http(base,'/metrics');before_resource=snapshot(pid)
        log=run/'server.log';log_offset=log.stat().st_size
        start=time.perf_counter()
        try:
            raw=http(base,'/completion',payload,case['timeout_s']);elapsed=time.perf_counter()-start
            atomic(dest/'native-response.json',raw,exclusive=True);record['native_response']=raw
            ids=raw.get('tokens');n=raw.get('tokens_predicted');tm=raw.get('timings',{})
            if type(ids)is not list or type(n)is not int or len(ids)!=n or tm.get('predicted_n')!=n or raw.get('stop')is not True:raise RuntimeError('MTP_NATIVE_OUTPUT_CONTRACT')
            if tm.get('cache_n')!=0 or tm.get('prompt_n')!=len(case['input_token_ids']) or raw.get('tokens_evaluated')!=len(case['input_token_ids']):raise RuntimeError('MTP_CACHE_OR_INPUT_CONTRACT')
            after_metrics=text_http(base,'/metrics')
            (dest/'metrics-before.txt').write_text(before_metrics);(dest/'metrics-after.txt').write_text(after_metrics)
            mb=metrics(before_metrics);ma=metrics(after_metrics);delta={k:v-mb.get(k,0) for k,v in ma.items()}
            if any(v<0 for v in delta.values()):raise RuntimeError('MTP_COUNTER_RESET')
            drafted=delta.get('llamacpp:spec_decode_num_draft_tokens_total')
            accepted=delta.get('llamacpp:spec_decode_num_accepted_tokens_total')
            if drafted is None or accepted is None or not 0<=accepted<=drafted:raise RuntimeError('MTP_COUNTERS_UNOBSERVABLE')
            if side=='OFF' and (drafted!=0 or accepted!=0):raise RuntimeError('OFF_PROCESS_DRAFTED')
            with log.open('rb') as f:f.seek(log_offset);segment=f.read().decode(errors='replace')
            (dest/'native-trace.log').write_text(segment)
            steps=[{'accepted':int(a),'drafted':int(b)} for a,b in re.findall(r'accepted\s+(\d+)\s*/\s*(\d+) draft tokens',segment)]
            if any(not 0<=x['accepted']<=x['drafted'] for x in steps):raise RuntimeError('INVALID_ACCEPTANCE_STEP')
            status=completion_state(raw.get('stop_type'),n,case['output_cap'],raw.get('content',''),case['phase'])
            if status in ('TECHNICAL_ERROR','OVER_OUTPUT') or elapsed>case['timeout_s']:raise RuntimeError('MTP_TERMINATION_OR_TIMEOUT')
            record.update(native_input_ids_echoed=None,input_validation='FROZEN_IDS_AND_NATIVE_TOKENIZER_MATCH',output_token_ids=ids,output_tokens=n,
                final_text=raw.get('content',''),reasoning_text='',finish_reason=raw['stop_type'],completion_status=status,
                native_prompt_processed=tm['prompt_n'],cache_reused_tokens=0,cache_gate_pass=True,
                request_latency_s=elapsed,observer='HTTP caller: submit to complete nonstreaming response read',
                engine_metrics={'native':tm,'decode_engine_tps':tm.get('predicted_per_second'),'prompt_engine_tps':tm.get('prompt_per_second'),
                   'decode_contract':'Native post-first token; prompt timing includes first-token sampling'},
                resource_before=before_resource,resource_after=snapshot(pid),metrics_delta=delta,
                draft_tokens=drafted,accepted_tokens=accepted,acceptance_steps=steps,
                partial_acceptance_observed=any(0<x['accepted']<x['drafted'] for x in steps),
                performance_admission='PENDING_ON_EQUIVALENCE' if side=='OFF' else 'AFTER_EQUIVALENCE_GATE',error=None)
            persist_result(dest,record,subrun,0);rows.append(record)
        except Exception as exc:
            if not (dest/'result.json').exists():persist_result(dest,error_record(record,exc,time.perf_counter()-start),subrun,0)
            atomic(subrun/'fatal.json',{'status':'TECHNICAL_ERROR','error':str(exc),'request_id':record['request_id'],'at':now()})
            raise
        if side=='ON' and case['phase']=='mtp_equivalence':
            off_path=off_run/'requests'/(case['phase']+'__'+key.removesuffix('-ON')+'-OFF')/'result.json'
            off=json.loads(off_path.read_text());pairs.append(compare_pair(off,record))
            atomic(subrun/'paired-progress.json',{'pairs':pairs,'at':now()})
    if side=='ON' and gate is None:
        gate=pair_gate(pairs,rows)
        atomic(subrun/'equivalence.json',gate,exclusive=True)
    summary={'status':'COMPLETE','side':side,'records':len(rows),'equivalence':gate,'at':now(),
             'partial_acceptance_observed':any(r['partial_acceptance_observed'] for r in rows),
             'speculative_tokens':sum(r['draft_tokens'] for r in rows),'accepted_tokens':sum(r['accepted_tokens'] for r in rows),
             'greedy_only':True,'sampled_equivalence':'NOT_TESTED','trace':'LLAMA_TRACE=1 process logging; no GPU profiler'}
    atomic(subrun/'summary.json',summary,exclusive=True)
    return summary


def collect_off(root,run,base,cfg,proc):
    return collect(root,run,base,cfg,proc.pid,'OFF')


def main_on():
    root=Path(os.environ['GS_ROOT']).resolve();run=Path(os.environ['GS_RUN_DIR'])
    frozen=verify_addendum(root);cfg=effective_cfg(root,'ON')
    for p,h in cfg['library_hashes'].items():
        if sha(p)!=h:raise RuntimeError('MTP_LIBRARY_PIN_CHANGED')
    if sha(cfg['binary']['path'])!=cfg['binary']['sha256']:raise RuntimeError('MTP_BINARY_PIN_CHANGED')
    proc=None;log=None
    def stop():
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=60)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=15)
    def interrupted(sig,frame):stop();raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    atomic(run/'quality.json',{'status':'NOT_EVALUATED'});atomic(run/'load.json',{'status':'IN_PROGRESS','at':now()})
    try:
        start=time.monotonic();log=(run/'server.log').open('x')
        proc=subprocess.Popen(cfg['command'],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'LLAMA_TRACE':'1'})
        base='http://127.0.0.1:'+str(cfg['port'])
        while time.monotonic()-start<cfg['load_timeout_s']:
            if proc.poll() is not None:raise RuntimeError('MTP_SERVER_EXIT:'+str(proc.returncode))
            try:
                if http(base,'/health',timeout=2).get('status')=='ok':break
            except Exception:pass
            time.sleep(1)
        else:raise TimeoutError('MTP_LOAD_TIMEOUT')
        resource=snapshot(proc.pid)
        if resource['memory_bytes']['MemAvailable']<cfg['minimum_memavailable_bytes']:raise RuntimeError('MTP_HEADROOM_GATE')
        atomic(run/'load.json',{'status':'PASS','pid':proc.pid,'load_s':time.monotonic()-start,'command':cfg['command'],'source_freeze':frozen,'memory_after':resource,'at':now()})
        summary=collect(root,run,base,cfg,proc.pid,'ON')
        atomic(run/'arm-result.json',summary,exclusive=True)
        atomic(run/'quality.json',{'status':'PASS','note':'collection completed; MTP equivalence may FAIL and is recorded separately','equivalence':summary['equivalence'],'at':now()})
        return 0
    except Exception as exc:
        atomic(run/'fatal.json',{'status':'TECHNICAL_ERROR','error':type(exc).__name__+':'+str(exc),'at':now()});raise
    finally:
        stop()
        if log:log.close()

if __name__=='__main__':raise SystemExit(main_on())
