"""Qualified MiMo original TP2 path, new frozen reasoning/request collector."""
from __future__ import annotations
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import time
from common import atomic,base_record,begin_request,completion_state,error_record,now,persist_result,plain,read_jsonl,sha,snapshot,split_reasoning,verify_freeze
from validate import sanity_verdict


def main():
    root=Path(os.environ['GS_ROOT']).resolve();run=Path(os.environ['GS_RUN_DIR']);rank=int(os.environ.get('RANK','0'));profile='O'
    frozen=verify_freeze(root);manifest=json.loads((root/'source-manifest.json').read_text());cfg=manifest['profiles'][profile]
    versions={name:importlib.metadata.version(name) for name in cfg['versions']}
    assert versions==cfg['versions'],'DEPENDENCY_PIN_MISMATCH'
    assert sha(Path(__file__).parent/'vllm_patch.py')==cfg['patch_sha256'],'QKV_PATCH_MISMATCH'
    for p,h in cfg['binary_hashes'].items():assert sha(p)==h,'NATIVE_LIBRARY_CHANGED'
    if (run/('arm-result.json' if rank==0 else 'arm-result-rank1.json')).exists():raise RuntimeError('RUN_ALREADY_COMPLETED')
    loadpath=run/('load.json' if rank==0 else 'load-rank1.json');phase='load';before=snapshot()
    atomic(loadpath,{'status':'IN_PROGRESS','started_at':now(),'memory_before':before,'source_freeze':frozen})
    if rank==0:atomic(run/'quality.json',{'status':'NOT_EVALUATED'})
    def alarm(sig,frame):raise TimeoutError('PREREGISTERED_REQUEST_DEADLINE')
    def interrupted(sig,frame):
        atomic(run/('fatal-rank'+str(rank)+'.json'),{'status':'INTERRUPTED','phase':phase,'signal':sig,'at':now()});raise SystemExit(128+sig)
    signal.signal(signal.SIGALRM,alarm);signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    import torch.distributed as dist
    from vllm import LLM,SamplingParams
    from tokenizers import Tokenizer
    from vllm_patch import apply_mimo26_vllm_patches
    apply_mimo26_vllm_patches()
    def barrier():
        if dist.is_initialized():dist.barrier()
    started=time.monotonic();llm=LLM(**cfg['kwargs']);load_s=time.monotonic()-started
    tok=llm.get_tokenizer();decoder=Tokenizer.from_file(str(root/cfg['tokenizer_json']))
    requests=read_jsonl(root/'requests-O.jsonl');checks={}
    for case in requests:
        key=case['input_ids_sha256']
        if key in checks:continue
        rendered=tok.apply_chat_template(case['messages'],tokenize=False,add_generation_prompt=True,enable_thinking=case['thinking'])
        ids=list(tok.encode(rendered,add_special_tokens=False))
        checks[key]={'actual_token_ids':ids,'rendered_match':rendered==case['rendered_text'],'match':ids==case['input_token_ids']}
        if ids!=case['input_token_ids'] or rendered!=case['rendered_text']:raise RuntimeError('RUNTIME_INPUT_MISMATCH:'+case['request_key'])
    atomic(run/('input-checks.json' if rank==0 else 'input-checks-rank1.json'),checks)
    engine=getattr(llm,'llm_engine',None);vc=getattr(engine,'vllm_config',None)
    mc=getattr(vc,'model_config',getattr(engine,'model_config',None));cc=getattr(vc,'cache_config',getattr(engine,'cache_config',None))
    actual={'max_model_len':getattr(mc,'max_model_len',None),'kv_cache_memory_bytes':getattr(cc,'kv_cache_memory_bytes',None),
            'num_gpu_blocks':getattr(cc,'num_gpu_blocks',None),'block_size':getattr(cc,'block_size',None)}
    if actual['max_model_len'] is not None and actual['max_model_len']!=16384:raise RuntimeError('ACTUAL_CONTEXT_MISMATCH')
    if actual['kv_cache_memory_bytes'] is not None and actual['kv_cache_memory_bytes']!=cfg['kwargs']['kv_cache_memory_bytes']:raise RuntimeError('ACTUAL_KV_BUDGET_MISMATCH')
    after=snapshot()
    if after['memory_bytes']['MemAvailable']<cfg['minimum_memavailable_bytes']:raise RuntimeError('POST_LOAD_HEADROOM_GATE')
    atomic(loadpath,{'status':'PASS','pid':os.getpid(),'rank':rank,'load_s':load_s,'finished_at':now(),'versions':versions,'kwargs':cfg['kwargs'],
        'actual_cache_context':actual,'source_freeze':frozen,'memory_before':before,'memory_after':after,'patch_sha256':cfg['patch_sha256']})
    completed=[];sanity={'preflight':[],'postflight':[]}
    try:
        for case in requests:
            phase=case['phase'];barrier()
            request_id,dest=begin_request(root,run,case,profile,rank,phase);record=base_record(root,run,case,profile,rank,phase,request_id)
            s=case['sampling'];params={'temperature':s['temperature'],'top_p':s['top_p'],'top_k':-1 if s['top_k']==0 else s['top_k'],'min_p':s['min_p'],'seed':s['seed'],
                'max_tokens':case['output_cap'],'repetition_penalty':s['repetition_penalty'],'presence_penalty':s['presence_penalty'],'frequency_penalty':s['frequency_penalty'],'ignore_eos':False}
            atomic(dest/'request.json',{'interface':'offline LLM.generate NONSTREAMING','input_token_ids':case['input_token_ids'],'sampling':params},exclusive=True)
            before_req=snapshot();t=time.perf_counter()
            try:
                signal.setitimer(signal.ITIMER_REAL,case['timeout_s'])
                try:outputs=llm.generate(case['input_token_ids'],SamplingParams(**params),use_tqdm=False)
                finally:signal.setitimer(signal.ITIMER_REAL,0)
                elapsed=time.perf_counter()-t
                raw=plain(outputs);atomic(dest/'native-response.json',raw,exclusive=True);record['native_response']=raw
                if len(outputs)!=1 or len(outputs[0].outputs)!=1:raise RuntimeError('NATIVE_RESPONSE_CARDINALITY')
                out=outputs[0];c=out.outputs[0];ids=list(c.token_ids);prompt=list(out.prompt_token_ids or []);cache=out.num_cached_tokens
                if prompt!=case['input_token_ids'] or cache!=0 or not out.finished:raise RuntimeError('INPUT_CACHE_OR_COMPLETION_CONTRACT')
                if getattr(out.metrics,'is_corrupted',False):raise RuntimeError('NATIVE_ENGINE_CORRUPTION')
                split=split_reasoning(c.text,ids,case['thinking'],cfg,decoder)
                status=completion_state(c.finish_reason,len(ids),case['output_cap'],split['final_text'],phase)
                metrics=plain(out.metrics)
                ft=getattr(out.metrics,'first_token_ts',None);lt=getattr(out.metrics,'last_token_ts',None);n=getattr(out.metrics,'num_generation_tokens',None)
                scheduled=getattr(out.metrics,'scheduled_ts',None)
                engine_metrics={'native':metrics,'decode_engine_tps':(n-1)/(lt-ft) if n and n>1 and ft and lt and lt>ft else None,
                    'decode_contract':'engine-core (num_generation_tokens-1)/(last_token_ts-first_token_ts)',
                    'engine_scheduled_to_first_s':ft-scheduled if ft and scheduled and ft>=scheduled else None,
                    'prompt_engine_s':None,'prompt_engine_tps':None,'first_generated_token_s':None,'first_final_token_s':None,'client_ttft_s':None}
                record.update(native_response=raw[0],native_input_ids_echoed=prompt,input_validation='NATIVE_ECHO_AND_RUNTIME_TOKENIZER',output_token_ids=ids,
                    output_tokens=len(ids),finish_reason=c.finish_reason,completion_status=status,cache_reused_tokens=cache,cache_gate_pass=True,
                    native_prompt_processed=len(prompt),request_latency_s=elapsed,observer='offline LLM.generate call to return on this rank',
                    t_submit=t,t_done=t+elapsed,engine_metrics=engine_metrics,resource_before=before_req,resource_after=snapshot(),error=None,**split)
                record['final_chars']=len(record['final_text']);record['final_bytes']=len(record['final_text'].encode());record['reasoning_chars']=len(record['reasoning_text'])
                if elapsed>case['timeout_s']:record.update(completion_status='TIMEOUT',error='RETURN_AFTER_FROZEN_DEADLINE')
                persist_result(dest,record,run,rank)
                if record['completion_status'] in ('TECHNICAL_ERROR','TIMEOUT','OVER_OUTPUT'):raise RuntimeError(record['error'] or record['completion_status'])
            except Exception as exc:
                signal.setitimer(signal.ITIMER_REAL,0)
                if not (dest/'result.json').exists():persist_result(dest,error_record(record,exc,time.perf_counter()-t),run,rank)
                raise
            completed.append({'request_id':request_id,'phase':phase,'case_id':case['case_id'],'completion_status':record['completion_status']})
            barrier()
            if rank==0 and phase in sanity:
                v=sanity_verdict(case['sanity_name'],record['final_text'],record['completion_status']);sanity[phase].append({'case_id':case['case_id'],**v})
                if len(sanity[phase])==6:
                    status='PASS' if all(x['status']=='PASS' for x in sanity[phase]) else 'FAIL'
                    atomic(run/('sanity-pre.json' if phase=='preflight' else 'sanity-post.json'),{'phase':phase,'status':status,'tests':sanity[phase],'at':now()})
                    if phase=='preflight':
                        atomic(run/'quality.json',{'status':'IN_PROGRESS' if status=='PASS' else 'FAIL','preflight':sanity[phase]})
                        if status!='PASS':raise RuntimeError('SANITY_PREFLIGHT_FAIL')
            if rank==0:atomic(run/'panel-progress.json',{'phase':phase,'records_completed':len(completed),'panel_completed':sum(x['phase']=='panel' for x in completed),'at':now()})
        if rank==0:
            quality='PASS' if len(sanity['postflight'])==6 and all(x['status']=='PASS' for x in sanity['postflight']) else 'FAIL'
            atomic(run/'quality.json',{'status':quality,'preflight':sanity['preflight'],'postflight':sanity['postflight'],'note':'Sanity/collection only, independent task verdicts pending'})
            atomic(run/'arm-result.json',{'profile':profile,'run_id':run.name,'requests':completed,'sanity':sanity,'source_freeze':frozen,'status':'COMPLETE','at':now()})
        else:atomic(run/'arm-result-rank1.json',{'profile':profile,'rank':rank,'requests':completed,'source_freeze':frozen,'status':'COMPLETE','at':now()})
        barrier()
        return 0 if rank!=0 or quality=='PASS' else 45
    except Exception as exc:
        atomic(run/('fatal-rank'+str(rank)+'.json'),{'phase':phase,'status':'TECHNICAL_ERROR','error':type(exc).__name__+':'+str(exc),'at':now()});raise

if __name__=='__main__':raise SystemExit(main())
