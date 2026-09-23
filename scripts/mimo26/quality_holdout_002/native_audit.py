# Native audit adapted from qualified001; original bytes archived in sources/qualified-001.
"""Recompute independent paired quality verdicts CPU-only, with no inference imports."""
from __future__ import annotations
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
from common import atomic,completion_state,digest,ids_sha,read_jsonl,sha,verify_freeze
from validate import same,sanity_verdict,verdict

FAIL={'FAIL_SEMANTIC','FAIL_FORMAT','FAIL_CODE_TEST'}
EVALUABLE={'PASS'}|FAIL


def paired_state(a,b):
    if a not in EVALUABLE or b not in EVALUABLE:return 'OTHER_STATES'
    if a=='PASS' and b=='PASS':return 'BOTH_PASS'
    if a in FAIL and b=='PASS':return 'A_FAIL_B_PASS'
    if a=='PASS' and b in FAIL:return 'A_PASS_B_FAIL'
    return 'BOTH_FAIL'


def check_record(rec,case,arm,index_sha,run,phase):
    errors=[]
    def require(cond,why):
        if not cond:errors.append(why)
    require(rec.get('record_sha256')==digest({k:v for k,v in rec.items() if k!='record_sha256'}),'record digest')
    require(rec.get('campaign')=='QUALITY-HOLDOUT-002' and rec.get('arm')==arm,'campaign/arm')
    require(rec.get('run_id')==run.name and rec.get('phase')==phase and rec.get('case_id')==case['case_id'],'run/phase/case')
    require(rec.get('source_index_sha256')==index_sha,'source freeze identity')
    require(same(rec.get('input_ids_provided'),case['input_token_ids']),'input ID list')
    require(rec.get('input_ids_sha256')==ids_sha(case['input_token_ids']),'input ID digest')
    require(rec.get('rendered_text')==case['rendered_text'] and rec.get('messages')==case['messages'],'prompt identity')
    require(rec.get('output_cap')==case['output_cap'],'cap changed')
    sampling=rec.get('sampling',{})
    require(sampling.get('temperature')==0 and sampling.get('seed')==1 and sampling.get('ignore_eos') is False and sampling.get('thinking') is False,'sampling changed')
    path=run/'requests'/(phase+'__'+case['case_id'])/'result.json'
    require(path.exists(),'atomic request result missing')
    if path.exists():require(json.loads(path.read_text())==rec,'append index differs from atomic record')
    status=rec.get('completion_status')
    if status in ('TECHNICAL_ERROR','TIMEOUT'):return errors
    raw=rec.get('native_response')
    require(isinstance(raw,dict),'native response missing')
    if not isinstance(raw,dict):return errors
    output_ids=rec.get('output_token_ids');n=rec.get('output_tokens')
    require(isinstance(output_ids,list) and type(n) is int and len(output_ids)==n,'native output ID count')
    require(rec.get('cache_reused_tokens')==0 and rec.get('cache_gate_pass') is True,'cache reuse gate')
    require(rec.get('native_prompt_processed')==len(case['input_token_ids']),'processed prompt count')
    require(rec.get('collector_consistency_pass') is True,'collector consistency')
    require(status==completion_state(rec.get('finish_reason'),n,case['output_cap']),'completion classification')
    require(rec.get('diagnostic_wall_s',float('inf'))<=case['timeout_s'],'deadline exceeded')
    if arm=='A':
        timings=raw.get('timings',{})
        require(raw.get('stop') is True and raw.get('content')==rec.get('final_text'),'A native terminal/content')
        require(raw.get('tokens')==output_ids and raw.get('tokens_predicted')==n and timings.get('predicted_n')==n,'A native output counters')
        require(timings.get('cache_n')==0 and timings.get('prompt_n')==len(case['input_token_ids']) and raw.get('tokens_evaluated')==len(case['input_token_ids']),'A native prompt/cache counters')
        require(raw.get('stop_type')==rec.get('finish_reason'),'A finish reason')
    else:
        outs=raw.get('outputs',[])
        require(raw.get('finished') is True,'B native finished')
        require(raw.get('prompt_token_ids')==case['input_token_ids'] and rec.get('native_input_ids_echoed')==case['input_token_ids'],'B native input echo')
        require(raw.get('num_cached_tokens')==0,'B native cache counter')
        require((raw.get('metrics') or {}).get('is_corrupted',False) is False,'B engine corruption flag')
        require(len(outs)==1,'B native output cardinality')
        if len(outs)==1:
            require(outs[0].get('token_ids')==output_ids and outs[0].get('text')==rec.get('final_text'),'B native content/IDs')
            require(outs[0].get('finish_reason')==rec.get('finish_reason'),'B finish reason')
    return errors


def load_arm(root,manifest,arm,cases,sanity):
    run=Path(manifest['runs'][arm]['run_dir']);index_sha=sha(root/'source-SHA256SUMS')
    p=run/'raw-results.jsonl';records=read_jsonl(p) if p.exists() else []
    inventory={};issues=[];counts=collections.Counter()
    for rec in records:
        key=(rec.get('phase'),rec.get('case_id'));counts[key]+=1
        inventory[key]=rec
    duplicates=[list(k) for k,n in counts.items() if n!=1]
    if duplicates:issues.append({'duplicate_request_keys':duplicates})
    allowed={('panel',c['case_id']) for c in cases}|{(phase,c['case_id']) for phase in ('preflight','postflight') for c in sanity}
    unexpected=[list(k) for k in inventory if k not in allowed]
    if unexpected:issues.append({'unexpected_requests':unexpected})
    full_order=[(phase,c['case_id']) for phase,items in [('preflight',sanity),('panel',cases),('postflight',sanity)] for c in items]
    actual_order=[(r.get('phase'),r.get('case_id')) for r in records]
    if actual_order!=full_order[:len(actual_order)]:issues.append({'request_order':'not expected frozen prefix'})
    config=run/'config.json'
    if not config.exists() or sha(config)!=sha(root/manifest['runs'][arm]['config']):issues.append({'config':'missing or changed'})
    input_checks=json.loads((run/'input-checks.json').read_text()) if (run/'input-checks.json').exists() else {}
    for c in cases+sanity:
        check=input_checks.get(c['case_id'],{})
        if check.get('actual_token_ids')!=c['input_token_ids']:
            issues.append({'runtime_tokenizer_check':c['case_id'],'reason':'not persisted or different'})
    results={};sanity_reports={}
    for phase,items in [('preflight',sanity),('panel',cases),('postflight',sanity)]:
        values=[]
        for case in items:
            rec=inventory.get((phase,case['case_id']))
            if rec is None:
                result={'status':'NOT_RUN','critical_violations':[],'reason':'No atomic request completion recovered'}
            else:
                errors=check_record(rec,case,arm,index_sha,run,phase)
                if counts[(phase,case['case_id'])]!=1:errors.append('duplicate completion record')
                if errors:
                    result={'status':'TECHNICAL_ERROR','critical_violations':[],'reason':'record integrity/contract','errors':errors}
                elif phase!='panel':result=sanity_verdict(case['name'],rec['final_text'],rec['completion_status'])
                else:result={'status':'PENDING_INDEPENDENT_VALIDATION'}
                result.update(request_id=rec['request_id'],record_sha256=rec['record_sha256'],
                    output_tokens=rec['output_tokens'],finish_reason=rec['finish_reason'],completion_status=rec['completion_status'],
                    raw_path=str(run/'requests'/(phase+'__'+case['case_id'])/'result.json'))
            if phase=='panel':results[case['case_id']]={'record':rec,'verdict':result}
            else:values.append({'case_id':case['case_id'],**result})
        if phase!='panel':sanity_reports[phase]={'status':'PASS' if len(values)==6 and all(v['status']=='PASS' for v in values) else 'FAIL_OR_MISSING','cases':values}
    terminal=json.loads((run/'result.json').read_text()) if (run/'result.json').exists() else {}
    restore=json.loads((run/'k2-after.json').read_text()) if (run/'k2-after.json').exists() else {}
    restore_pass=(terminal.get('cleanup',{}).get('status')=='PASS' and restore.get('state')=='READY'
        and restore.get('release_id')==manifest['restore']['release_id'] and restore.get('preset')==manifest['restore']['preset']
        and restore.get('owner')=='DS41' and restore.get('owner_state')=='RUNNING'
        and restore.get('paired_backend_http')=='200' and len(restore.get('ranks',[]))==2
        and all(r.get('active') is True and r.get('health_http')=='200' for r in restore['ranks']))
    meta={'run_id':run.name,'raw_path':str(p),'raw_sha256':sha(p) if p.exists() else None,'raw_records':len(records),
        'issues':issues,'sanity':sanity_reports,'run_completion':terminal.get('run_completion','NOT_STARTED'),
        'initial_cause':terminal.get('initial_cause'),'cleanup':terminal.get('cleanup'),
        'restore_receipt':restore,'restore_pass':restore_pass,'launch_count':int((run/'launch-count.txt').read_text()) if (run/'launch-count.txt').exists() else 0,
        'load':json.loads((run/'load.json').read_text()) if (run/'load.json').exists() else None}
    return results,meta,records

