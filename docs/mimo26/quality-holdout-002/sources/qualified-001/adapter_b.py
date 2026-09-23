"""New frozen B collector: qualified vLLM offline TP2, one model load per rank."""
from __future__ import annotations
import importlib.metadata
import json
import os
import signal
import time
from pathlib import Path
from common import (atomic,base_result,begin_request,completion_state,failure_record,now,
                    persist_result,plain,read_jsonl,sha,snapshot,verify_freeze)
from validate import sanity_verdict


def main():
    root=Path(os.environ['QR_ROOT']);run=Path(os.environ['QR_RUN_DIR'])
    arm='B';rank=int(os.environ.get('RANK','0'))
    frozen=verify_freeze(root)
    manifest=json.loads((root/'source-manifest.json').read_text());cfg=manifest['runtimes']['B']
    versions={name:importlib.metadata.version(name) for name in cfg['versions']}
    if versions!=cfg['versions']:raise RuntimeError('B_DEPENDENCY_PIN_MISMATCH')
    if sha(Path(__file__).parent/'vllm_patch.py')!=cfg['patch_sha256']:raise RuntimeError('B_PATCH_PIN_MISMATCH')
    cases=read_jsonl(root/'cases.jsonl');sanity=read_jsonl(root/'sanity.jsonl')
    phase='load';before=snapshot()
    load_path=run/('load.json' if rank==0 else 'load-rank1.json')
    atomic(load_path,{'status':'IN_PROGRESS','started_at':now(),'memory_before':before,'source_freeze':frozen})
    if rank==0:atomic(run/'quality.json',{'status':'NOT_EVALUATED'})
    def alarm(sig,frame):raise TimeoutError('B_REQUEST_PREREGISTERED_DEADLINE')
    signal.signal(signal.SIGALRM,alarm)
    def interrupted(sig,frame):
        atomic(run/f'fatal-rank{rank}.json',{'status':'INTERRUPTED','phase':phase,'signal':sig,'at':now()})
        raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    # Imports and LLM initialization occur only after source/version checks, never in CPU tests.
    import torch.distributed as dist
    from vllm import LLM,SamplingParams
    from vllm_patch import apply_mimo26_vllm_patches
    apply_mimo26_vllm_patches()
    def barrier():
        if dist.is_initialized():dist.barrier()
    started=time.perf_counter()
    llm=LLM(**cfg['kwargs'])
    load_s=time.perf_counter()-started
    tok=llm.get_tokenizer()
    checks={}
    for case in sanity+cases:
        rendered=tok.apply_chat_template(case['messages'],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        got=list(tok.encode(rendered,add_special_tokens=False))
        checks[case['case_id']]={'rendered_match':rendered==case['rendered_text'],
            'ids_match':got==case['input_token_ids'],'actual_token_ids':got,'count':len(got)}
        if not checks[case['case_id']]['rendered_match'] or got!=case['input_token_ids']:
            raise RuntimeError('B_TOKENIZER_MISMATCH:'+case['case_id'])
    atomic(run/('input-checks.json' if rank==0 else 'input-checks-rank1.json'),checks)
    atomic(load_path,{'status':'PASS','load_s':load_s,'finished_at':now(),'pid':os.getpid(),
        'rank':rank,'runtime_versions':versions,'kwargs':cfg['kwargs'],'patch_sha256':cfg['patch_sha256'],
        'memory_before':before,'memory_after':snapshot(),'source_freeze':frozen})
    def generate(case,phase):
        barrier()
        request_id,dest=begin_request(run,case,arm,rank,phase,root)
        result=base_result(run,case,arm,rank,phase,request_id,root)
        result['runtime']={'name':'vLLM','versions':versions,'patch_sha256':cfg['patch_sha256']}
        params={'temperature':0.0,'seed':1,'max_tokens':case['output_cap'],'repetition_penalty':1.0,
                'presence_penalty':0.0,'frequency_penalty':0.0,'ignore_eos':False}
        atomic(dest/'request.json',{'interface':'offline LLM.generate','input_token_ids':case['input_token_ids'],'sampling':params},exclusive=True)
        before_req=snapshot();start=time.perf_counter()
        try:
            signal.setitimer(signal.ITIMER_REAL,case['timeout_s'])
            try:output=llm.generate(case['input_token_ids'],SamplingParams(**params),use_tqdm=False)
            finally:signal.setitimer(signal.ITIMER_REAL,0)
            elapsed=time.perf_counter()-start
            if len(output)!=1 or len(output[0].outputs)!=1:raise RuntimeError('MISSING_OR_MULTIPLE_NATIVE_RESULT')
            out=output[0];choice=out.outputs[0];ids=list(choice.token_ids)
            prompt_ids=list(out.prompt_token_ids or []);cache=out.num_cached_tokens
            status=completion_state(choice.finish_reason,len(ids),case['output_cap'])
            result.update(native_response=plain(out),final_text=choice.text,output_tokens=len(ids),output_token_ids=ids,
                native_output_ids_available=True,native_input_ids_echoed=prompt_ids,
                input_validation='NATIVE_INPUT_IDS_ECHO_MATCH',finish_reason=choice.finish_reason,
                completion_status=status,cache_reused_tokens=cache,cache_gate_pass=(cache==0),
                native_prompt_processed=len(prompt_ids)-cache if type(cache) is int else None,
                diagnostic_wall_s=elapsed,diagnostic_clock='perf_counter around offline LLM.generate on this rank',
                t_submit_monotonic=start,t_done_monotonic=start+elapsed,resource_before=before_req,
                resource_after=snapshot(),collector_consistency_pass=(prompt_ids==case['input_token_ids']),error=None)
            if cache!=0 or prompt_ids!=case['input_token_ids'] or status=='TECHNICAL_ERROR' or getattr(out.metrics,'is_corrupted',False):
                result['completion_status']='TECHNICAL_ERROR';result['error']='CACHE_OR_INPUT_CONTRACT_FAILURE'
            if elapsed>case['timeout_s']:
                result['completion_status']='TIMEOUT';result['error']='COMPLETION_AFTER_PREREGISTERED_DEADLINE'
            persist_result(dest,result,run,rank)
            if result['completion_status'] in ('TECHNICAL_ERROR','TIMEOUT'):raise RuntimeError(result['error'])
            barrier()
            return result
        except Exception as e:
            signal.setitimer(signal.ITIMER_REAL,0)
            if not (dest/'result.json').exists():persist_result(dest,failure_record(result,e),run,rank)
            raise
    def sanity_phase(phase):
        tests=[]
        for case in sanity:
            response=generate(case,phase)
            if rank==0:
                value=sanity_verdict(case['name'],response['final_text'],response['completion_status'])
                tests.append({'case_id':case['case_id'],'request_id':response['request_id'],**value})
        report={'phase':phase,'status':'PASS' if rank==0 and all(x['status']=='PASS' for x in tests) else 'NOT_EVALUATED_ON_PEER',
                'tests':tests,'at':now()}
        if rank==0:
            report['status']='PASS' if len(tests)==6 and all(x['status']=='PASS' for x in tests) else 'FAIL'
            atomic(run/('sanity-pre.json' if phase=='preflight' else 'sanity-post.json'),report)
        return report
    try:
        phase='preflight';pre=sanity_phase(phase)
        if rank==0:
            if pre['status']!='PASS':
                atomic(run/'quality.json',{'status':'FAIL','preflight':pre,'postflight':None});raise RuntimeError('SANITY_PREFLIGHT_FAIL')
            atomic(run/'quality.json',{'status':'IN_PROGRESS','preflight':pre,'postflight':None})
        barrier()
        phase='panel';panel=[]
        for case in cases:
            rec=generate(case,phase);panel.append({'case_id':case['case_id'],'request_id':rec['request_id'],'completion_status':rec['completion_status'],'output_tokens':rec['output_tokens']})
            if rank==0:atomic(run/'panel-progress.json',{'status':'IN_PROGRESS','completed':len(panel),'planned':len(cases),'last_case':case['case_id'],'at':now()})
        phase='postflight';post=sanity_phase(phase)
        if rank==0:
            quality={'status':'PASS' if post['status']=='PASS' else 'FAIL','preflight':pre,'postflight':post,'panel_completions':len(panel),
                     'note':'PASS denotes sanity and collection, not independent panel verdicts'}
            atomic(run/'quality.json',quality)
            atomic(run/'arm-result.json',{'schema':'mimo26-quality-arm-v1','arm':arm,'run_id':run.name,'panel':panel,
                'sanity_pre':pre,'sanity_post':post,'source_freeze':frozen,'at':now()})
            atomic(run/'panel-progress.json',{'status':'COMPLETE','completed':len(panel),'planned':len(cases),'at':now()})
        else:atomic(run/'arm-result-rank1.json',{'arm':arm,'rank':rank,'panel':panel,'source_freeze':frozen,'at':now()})
        barrier()
        return 0 if rank!=0 or post['status']=='PASS' else 45
    except Exception as e:
        atomic(run/f'fatal-rank{rank}.json',{'status':'TECHNICAL_ERROR','phase':phase,'error':type(e).__name__+':'+str(e),'at':now()})
        raise

if __name__=='__main__':raise SystemExit(main())
