"""Frozen CPU-only selection evaluator. Never imports or calls inference engines."""
from __future__ import annotations
import argparse
import collections
import json
import math
from pathlib import Path
import statistics
from common import atomic,completion_state,digest,ids_sha,read_jsonl,sha,verify_freeze
from validate import verdict,sanity_verdict,same

PROFILES=('Q','M','D','O')


def stats(values):
    xs=[float(x) for x in values if x is not None and math.isfinite(float(x))]
    return {'n':len(xs),'median':statistics.median(xs) if xs else None,'min':min(xs) if xs else None,'max':max(xs) if xs else None,'sum':sum(xs) if xs else None}


def record_audit(root,run,profile,plan,record):
    errors=[]
    def require(cond,name):
        if not cond:errors.append(name)
    require(record.get('record_sha256')==digest({k:v for k,v in record.items() if k!='record_sha256'}),'record digest')
    require(record.get('campaign')=='STRIX-GENERALIST-SELECTION-001' and record.get('profile')==profile and record.get('run_id')==run.name,'identity')
    require(record.get('phase')==plan['phase'] and record.get('case_id')==plan['case_id'] and record.get('request_key')==plan['request_key'],'request identity')
    require(record.get('source_index_sha256')==sha(root/'source-SHA256SUMS'),'freeze digest')
    for key in ['messages','rendered_text','input_token_ids','input_ids_sha256','output_cap','thinking','sampling','timeout_s']:
        require(same(record.get(key),plan[key]),'request contract '+key)
    require(record.get('input_ids_sha256')==ids_sha(plan['input_token_ids']),'input digest')
    path=run/'requests'/(plan['phase']+'__'+plan['request_key'])/'result.json'
    require(path.exists() and json.loads(path.read_text())==record,'atomic record matches append log')
    if record.get('completion_status') in ('TECHNICAL_ERROR','TIMEOUT'):return errors
    native=record.get('native_response');require(type(native) is dict,'native response')
    if not isinstance(native,dict):return errors
    n=record.get('output_tokens');require(type(n) is int and n>=0,'native output count')
    require(record.get('cache_reused_tokens')==0 and record.get('cache_gate_pass') is True,'cache reuse')
    require(record.get('native_prompt_processed')==len(plan['input_token_ids']),'processed prompt')
    require(record.get('completion_status')==completion_state(record.get('finish_reason'),n,plan['output_cap'],record.get('final_text',''),plan['phase']),'completion status')
    require(record.get('request_latency_s',float('inf'))<=plan['timeout_s'],'request deadline')
    if profile in ('Q','M'):
        require(type(record.get('output_token_ids')) is list and len(record['output_token_ids'])==n,'output IDs')
        require(native.get('tokens')==record.get('output_token_ids') and native.get('tokens_predicted')==n,'native output identity')
        require(native.get('stop') is True and native.get('stop_type')==record.get('finish_reason'),'native terminal')
        tm=native.get('timings',{})
        require(tm.get('cache_n')==0 and tm.get('prompt_n')==len(plan['input_token_ids']) and tm.get('predicted_n')==n,'native counters')
    elif profile=='O':
        require(native.get('finished') is True and native.get('num_cached_tokens')==0,'O native completion/cache')
        require(native.get('prompt_token_ids')==plan['input_token_ids'],'O native prompt echo')
        outs=native.get('outputs',[]);require(len(outs)==1,'O output cardinality')
        if len(outs)==1:require(outs[0].get('token_ids')==record.get('output_token_ids') and len(outs[0].get('token_ids',[]))==n and outs[0].get('finish_reason')==record.get('finish_reason'),'O native output')
        require((native.get('metrics') or {}).get('is_corrupted',False) is False,'O numerical corruption')
    else:
        require(record.get('output_token_ids') is None and record.get('reasoning_tokens_native') is None and record.get('final_tokens_native') is None,'D unavailable fields not fabricated')
        usage=native.get('usage',{});require(usage.get('completion_tokens')==n and usage.get('prompt_tokens')==len(plan['input_token_ids']),'D native usage')
        require((usage.get('prompt_tokens_details') or {}).get('cached_tokens')==0,'D native cache')
        tr=record.get('native_trace_audit',{});require(tr.get('rendered_match') is True and tr.get('generated_tokens')==n,'D native trace')
        msg=native.get('choices',[{}])[0].get('message',{})
        require((msg.get('content') or '')==record.get('final_text') and (msg.get('reasoning_content') or '')==record.get('reasoning_text'),'D native final/reasoning')
    return errors


def restore_pass(run,manifest):
    result=json.loads((run/'result.json').read_text()) if (run/'result.json').exists() else {}
    state=json.loads((run/'k2-after.json').read_text()) if (run/'k2-after.json').exists() else {}
    target=manifest['restore']
    return (result.get('cleanup',{}).get('status')=='PASS' and state.get('state')=='READY' and state.get('preset')==target['preset'] and state.get('release_id')==target['release_id']
            and state.get('owner')=='DS41' and state.get('owner_state')=='RUNNING' and state.get('paired_backend_http')=='200'
            and len(state.get('ranks',[]))==2 and all(x.get('active') is True and x.get('health_http')=='200' for x in state['ranks']))


def load_profile(root,manifest,profile):
    run=Path(manifest['runs'][profile]['run_dir']);plans=read_jsonl(root/('requests-'+profile+'.jsonl'))
    p=run/'raw-results.jsonl';records=read_jsonl(p) if p.exists() else [];index={};counts=collections.Counter();issues=[]
    for rec in records:
        key=(rec.get('phase'),rec.get('request_key'));counts[key]+=1;index[key]=rec
    if any(v!=1 for v in counts.values()):issues.append('duplicate request identity')
    desired=[(x['phase'],x['request_key']) for x in plans]
    actual=[(x.get('phase'),x.get('request_key')) for x in records]
    if actual!=desired[:len(actual)]:issues.append('request order is not the frozen prefix')
    if (run/'config.json').exists() and sha(run/'config.json')!=sha(root/manifest['runs'][profile]['config']):issues.append('run configuration changed')
    result=json.loads((run/'result.json').read_text()) if (run/'result.json').exists() else {}
    load=json.loads((run/'load.json').read_text()) if (run/'load.json').exists() else {}
    if load.get('status')=='PASS':
        sf=load.get('source_freeze',{});loaded=sf.get('loaded_modules',{})
        adapter='adapter_llama.py' if profile in ('Q','M') else 'adapter_ds41.py' if profile=='D' else 'adapter_original.py'
        if sf.get('index_sha256')!=sha(root/'source-SHA256SUMS'):issues.append('runtime source index mismatch')
        for name,filename in [('__main__',adapter),('common','common.py'),('validate','validate.py')]:
            item=loaded.get(name,{})
            if item.get('sha256')!=sha(root/'sources'/filename) or item.get('path')!=str((root/'sources'/filename).resolve()):issues.append('runtime frozen import mismatch:'+name)
    values={};sanity={'preflight':[],'postflight':[]};bench=[];warmup=[]
    for plan in plans:
        rec=index.get((plan['phase'],plan['request_key']))
        if rec is None:v={'status':'NOT_RUN','critical_violations':[],'reason':'No completed atomic request exists'}
        else:
            failures=record_audit(root,run,profile,plan,rec)
            if failures:v={'status':'TECHNICAL_ERROR','critical_violations':[],'record_errors':failures}
            elif rec['completion_status'] in ('TECHNICAL_ERROR','TIMEOUT','INCOMPLETE_OUTPUT_CAP','INCOMPLETE_NO_FINAL','OVER_OUTPUT'):v={'status':rec['completion_status'],'critical_violations':[],'reason':rec.get('error')}
            elif plan['phase'] in sanity:v=sanity_verdict(plan['sanity_name'],rec['final_text'],rec['completion_status'])
            else:v={'status':'PENDING' if plan['phase']=='panel' else rec['completion_status'],'critical_violations':[]}
            v.update(request_id=rec['request_id'],raw_path=str(run/'requests'/(plan['phase']+'__'+plan['request_key'])/'result.json'),record_sha256=rec['record_sha256'],
                     request_latency_s=rec.get('request_latency_s'),output_tokens=rec.get('output_tokens'),reasoning_tokens_native=rec.get('reasoning_tokens_native'),
                     final_tokens_native=rec.get('final_tokens_native'),reasoning_chars=rec.get('reasoning_chars'),final_chars=rec.get('final_chars'),observer=rec.get('observer'))
        if plan['phase']=='panel':values[plan['case_id']]={'verdict':v,'record':rec}
        elif plan['phase'] in sanity:sanity[plan['phase']].append({'case_id':plan['case_id'],**v})
        else:
            row={'case_id':plan['case_id'],'request_key':plan['request_key'],'phase':plan['phase'],'input_tokens':plan['input_tokens'],'input_bytes':plan['input_bytes'],**v,
                 'engine_metrics':rec.get('engine_metrics') if rec else None,'resource_before':rec.get('resource_before') if rec else None,'resource_after':rec.get('resource_after') if rec else None,
                 'peer_resource_before':rec.get('peer_resource_before') if rec else None,'peer_resource_after':rec.get('peer_resource_after') if rec else None}
            (bench if plan['phase']=='benchmark' else warmup).append(row)
    peer={}
    if profile=='O':
        pp=root/'evidence/O-rank1-raw-results.jsonl'
        if pp.exists():
            rows=read_jsonl(pp);primary={(r['phase'],r['request_key']):r for r in records};peer_errors=[]
            for rec in rows:
                other=primary.get((rec.get('phase'),rec.get('request_key')))
                if other is None or any(not same(rec.get(k),other.get(k)) for k in ['input_token_ids','output_token_ids','final_text','reasoning_text','finish_reason','completion_status','source_index_sha256']):peer_errors.append(rec.get('request_id'))
                if rec.get('record_sha256')!=digest({k:v for k,v in rec.items() if k!='record_sha256'}):peer_errors.append('digest')
            peer={'status':'PASS' if len(rows)==len(records)==32 and not peer_errors else 'FAIL_OR_PARTIAL','count':len(rows),'errors':peer_errors,'sha256':sha(pp)}
        else:peer={'status':'NOT_AVAILABLE'}
    benchmarks={}
    for name in ('ENGINE-2K','ENGINE-8K'):
        group=[r for r in bench if r['case_id']==name];valid=[r for r in group if r['status']=='VALID_CAP']
        benchmarks[name]={'planned':3,'n_valid':len(valid),'all_samples':group,
            'request_latency_s':stats(r.get('request_latency_s') for r in valid),
            'prompt_engine_tps':stats((r.get('engine_metrics') or {}).get('prompt_engine_tps') for r in valid),
            'decode_post_first_engine_tps':stats((r.get('engine_metrics') or {}).get('decode_engine_tps') for r in valid),
            'D_decode_total_rate_rounded':stats((r.get('engine_metrics') or {}).get('decode_engine_total_rate_rounded') for r in valid),
            'input_tokens':[r['input_tokens'] for r in group],'input_bytes':[r['input_bytes'] for r in group]}
    meta={'name':manifest['profiles'][profile]['name'],'nodes':manifest['profiles'][profile]['nodes'],'run_dir':str(run),'run_completion':result.get('run_completion','NOT_STARTED'),
          'initial_cause':result.get('initial_cause'),'cleanup':result.get('cleanup'),'restore_pass':restore_pass(run,manifest),'raw_records':len(records),
          'launch_count':int((run/'launch-count.txt').read_text()) if (run/'launch-count.txt').exists() else 0,'load':load,
          'sanity':{k:{'status':'PASS' if len(v)==6 and all(x['status']=='PASS' for x in v) else 'FAIL_OR_MISSING','cases':v} for k,v in sanity.items()},
          'issues':issues,'peer':peer,'benchmarks':benchmarks,'warmups':warmup,'source_raw_sha256':sha(p) if p.exists() else None}
    meta['runtime_qualification']='PASS' if load.get('status')=='PASS' and not issues and all(x['status']=='PASS' for x in meta['sanity'].values()) and (profile!='O' or peer.get('status')=='PASS') else 'NOT_QUALIFIED_OR_INCOMPLETE'
    return values,meta,records


def compute(root):
    root=Path(root).resolve();freeze=verify_freeze(root);manifest=json.loads((root/'source-manifest.json').read_text())
    preparation=json.loads((root/'preparation.json').read_text());assert preparation['source_index_sha256']==freeze['index_sha256']
    cases=read_jsonl(root/'cases.jsonl');oracles={x['case_id']:x for x in read_jsonl(root/'expected.jsonl')}
    assert len(cases)==12 and [c['case_id'] for c in cases]==manifest['case_order']
    invalid=json.loads((root/'case-invalid.json').read_text()) if (root/'case-invalid.json').exists() else {}
    if any(k not in oracles or not isinstance(v,str) or not v.strip() for k,v in invalid.items()):raise ValueError('invalid symmetric case-invalid review')
    values={};profiles={};raw=[]
    for profile in PROFILES:
        values[profile],profiles[profile],records=load_profile(root,manifest,profile)
        raw.extend({'role':'DERIVED_INDEX_OF_ORIGINAL_RECORD','profile':profile,'source_file':profiles[profile]['run_dir']+'/raw-results.jsonl','record':r} for r in records)
    pairs=[]
    for case in cases:
        row={'case_id':case['case_id'],'family':case['family'],'language':case['language'],'title':case['title'],'cap':case['output_cap'],'profiles':{}}
        for profile in PROFILES:
            item=values[profile][case['case_id']];v=dict(item['verdict'])
            if case['case_id'] in invalid:v.update(status='CASE_INVALID',reason=invalid[case['case_id']],critical_violations=[])
            elif v['status']=='PENDING':v.update(verdict(item['record']['final_text'],oracles[case['case_id']],item['record']['completion_status']))
            row['profiles'][profile]=v
        row['successful_profiles']=[p for p in PROFILES if row['profiles'][p]['status']=='PASS']
        pairs.append(row)
    for profile,meta in profiles.items():
        rows=[r['profiles'][profile] for r in pairs]
        meta['quality_counts']=dict(collections.Counter(v['status'] for v in rows));meta['quality_planned']=12
        meta['per_family']={f:dict(collections.Counter(r['profiles'][profile]['status'] for r in pairs if r['family']==f)) for f in sorted({r['family'] for r in pairs})}
        meta['critical_violations']=sum(len(v.get('critical_violations',[])) for v in rows)
        meta['all_task_time_s']=stats(v.get('request_latency_s') for v in rows)
        meta['successful_task_time_s']=stats(v.get('request_latency_s') for v in rows if v['status']=='PASS')
        meta['failed_or_incomplete_task_time_s']=stats(v.get('request_latency_s') for v in rows if v['status']!='PASS')
        meta['output_tokens_total']=sum(v.get('output_tokens') or 0 for v in rows)
        meta['reasoning_tokens_native_total']=None if any(v.get('reasoning_tokens_native') is None for v in rows) else sum(v['reasoning_tokens_native'] for v in rows)
        meta['final_tokens_native_total']=None if any(v.get('final_tokens_native') is None for v in rows) else sum(v['final_tokens_native'] for v in rows)
        meta['observer_group']='OFFLINE_GENERATE' if profile=='O' else 'HTTP_NONSTREAM'
    comparisons={}
    for a in PROFILES:
        for b in PROFILES:
            if a>=b:continue
            counts=collections.Counter()
            for row in pairs:
                av=row['profiles'][a]['status'];bv=row['profiles'][b]['status']
                if av=='PASS' and bv=='PASS':k='BOTH_PASS'
                elif av=='PASS' and bv.startswith('FAIL'):k='A_PASS_B_FAIL'
                elif bv=='PASS' and av.startswith('FAIL'):k='A_FAIL_B_PASS'
                elif av.startswith('FAIL') and bv.startswith('FAIL'):k='BOTH_FAIL'
                else:k='INCOMPLETE_OR_TECHNICAL'
                counts[k]+=1
            comparisons[a+'_'+b]={'pair_counts':dict(counts),'same_latency_observer':profiles[a]['observer_group']==profiles[b]['observer_group'],
                'timing_ratio':None,'note':'No HTTP/offline normalized ratio or stochastic superiority claim.'}
    dominated=[]
    for a in PROFILES:
        for b in PROFILES:
            if a==b or profiles[a]['observer_group']!=profiles[b]['observer_group']:continue
            pa=profiles[a];pb=profiles[b]
            if pa['runtime_qualification']==pb['runtime_qualification']=='PASS' and pa['all_task_time_s']['n']==pb['all_task_time_s']['n']==12 and pa['quality_counts'].get('PASS',0)<pb['quality_counts'].get('PASS',0) and pa['all_task_time_s']['sum']>pb['all_task_time_s']['sum']:
                dominated.append({'profile':a,'dominated_by':b,'scope':'This one-sample-per-task panel and matching local HTTP observer only; not universal dominance'})
    complete=all(p['raw_records']==32 and p['run_completion']=='PASS' and p['launch_count']==1 and p['runtime_qualification']=='PASS' and not p['issues'] for p in profiles.values())
    blockers=json.loads((root/'blockers.json').read_text()) if (root/'blockers.json').exists() else {}
    live=json.loads((root/'final-live.json').read_text()) if (root/'final-live.json').exists() else {'status':'NOT_VERIFIED'}
    gates={'EXPERIMENT_COLLECTION':'COMPLETE' if complete else 'PARTIAL_OR_BLOCKED','SOURCE_FREEZE':'PASS','TASK_COUNT':12,
        'GENERAL_EQUIVALENCE':'NOT_ESTABLISHED','THINKING_CAUSAL_EFFECT':'NOT_ISOLATED','QUANTIZATION_ONLY_EFFECT':'NOT_ISOLATED',
        'SAMPLED_VARIANCE':'NOT_EVALUATED','LONG_CONTEXT':'NOT_QUALIFIED','PRODUCTION_PROMOTION':'NOT_PERFORMED',
        'MTP':manifest['mtp']['status'],'FINAL_RESIDENT':live.get('status')}
    return {'schema':'strix-generalist-summary-v1','campaign':manifest['campaign'],'freeze':freeze,'preparation':preparation,'gates':gates,'profiles':profiles,
        'cases':pairs,'comparisons':comparisons,'dominated_observations':dominated,'blockers':blockers,'mtp':manifest['mtp'],'final_live':live,
        'limitations':['Twelve new synthetic tasks, one sampled generation per profile; no statistical superiority or variance estimate.',
        'D exposes native total generation count but not native generated IDs or separate reasoning/final counts; unavailable fields remain null.',
        'Engine tasks have thinking OFF and must not replace reasoning task elapsed times.',
        'Source manifests, timing observers and runtime configurations differ by model; the original O is not an oracle.']},raw


def render(summary):
    lines=['# STRIX-GENERALIST-SELECTION-001','', '**Collection:** '+summary['gates']['EXPERIMENT_COLLECTION']+'. Scores are separate from execution and restore.','',
      '## Quality and operating cost','', '| Profile | Runtime qualification | Nodes | PASS / 12 | Other states | All task seconds | Successful task seconds | Native output tokens |',
      '|---|---|---:|---:|---|---:|---:|---:|']
    for name,p in summary['profiles'].items():
        other={k:v for k,v in p['quality_counts'].items() if k!='PASS'}
        lines.append(f"| {name} — {p['name']} | {p['runtime_qualification']} | {p['nodes']} | {p['quality_counts'].get('PASS',0)} | {json.dumps(other)} | {p['all_task_time_s']['sum']} | {p['successful_task_time_s']['sum']} | {p['output_tokens_total']} |")
    lines+=['','Times include failed and incomplete requests. O is an offline-generate observer; Q/M/D are local HTTP observers. No cross-observer normalized ratio is reported.','', '## All twelve matched tasks','', '| Case | Family | Q | M | D | O |','|---|---|---|---|---|---|']
    for row in summary['cases']:lines.append('| '+row['case_id']+' | '+row['family']+' | '+' | '.join(row['profiles'][p]['status'] for p in PROFILES)+' |')
    lines+=['','## Per-family results','']
    for name,p in summary['profiles'].items():lines+=['### '+name,'','```json',json.dumps(p['per_family'],indent=2),'```','']
    lines+=['## Failures and incomplete responses','']
    for row in summary['cases']:
        for name,v in row['profiles'].items():
            if v['status']=='PASS':continue
            lines+=['### '+row['case_id']+' / '+name+' — '+v['status'],'', 'Original: `'+v.get('raw_path','NOT_RUN')+'`.','```json',json.dumps({k:v[k] for k in ['reason','record_errors','critical_violations','diagnostics'] if k in v},ensure_ascii=False,indent=2),'```','']
    lines+=['## Engine tasks, separate from reasoning quality','', '| Profile / input | n valid / 3 | Prompt engine tok/s median | Decode post-first engine tok/s median | D total decode rate (rounded native log) | Local request seconds median |','|---|---:|---:|---:|---:|---:|']
    for name,p in summary['profiles'].items():
        for length,b in p['benchmarks'].items():lines.append(f"| {name} / {length} | {b['n_valid']} | {b['prompt_engine_tps']['median']} | {b['decode_post_first_engine_tps']['median']} | {b['D_decode_total_rate_rounded']['median']} | {b['request_latency_s']['median']} |")
    lines+=['','All replicas, ranges, native timing contracts, actual input token/byte counts and resource snapshots are retained in summary.json. SHORT_OUTPUT is not padded. No client TTFT is invented. D rounded log totals are not the post-first-token metric.','', '## Collection, sanity and restore','']
    for name,p in summary['profiles'].items():lines.append(name+': '+json.dumps({'run':p['run_dir'],'collection':p['run_completion'],'records':p['raw_records'],'launches':p['launch_count'],'sanity':{k:v['status'] for k,v in p['sanity'].items()},'restore':p['restore_pass'],'cleanup':p['cleanup'],'issues':p['issues']},ensure_ascii=False))
    lines+=['','## Blockers and bounded MTP','', '```json',json.dumps({'profiles':summary['blockers'],'mtp':summary['mtp']},ensure_ascii=False,indent=2),'```','',
       '## Interpretation limits','']+summary['limitations']+['','Static same-request two-node feasibility and the single next action are in COOPERATION.md and NEXT_EXACT_ACTION.md. No HaloPipe port, additional distributed workload, deployment or push is performed.','',
       '## CPU-only reproducibility','', '```bash','cd /home/funboy/StrixHaloMimo26','PYTHONDONTWRITEBYTECODE=1 python3 docs/selection/strix-generalist-selection-001/sources/evaluate.py --root docs/selection/strix-generalist-selection-001 --check','```',
       'Requires original native run paths and the pinned existing Podman image for code tests. This command is claimed verified only when verification.json records its successful exit.','']
    return '\n'.join(lines)


def outputs(summary,raw):
    return {'summary.json':json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+'\n','REPORT.md':render(summary),
            'paired-results.jsonl':''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in summary['cases']),
            'raw-results.jsonl':''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in raw)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--write',action='store_true');g.add_argument('--check',action='store_true');a=p.parse_args()
    summary,raw=compute(a.root);files=outputs(summary,raw)
    for name,text in files.items():
        path=a.root/name
        if a.write:path.write_text(text)
        elif path.read_text()!=text:raise AssertionError('RECALCULATION_MISMATCH:'+name)
    print(json.dumps({'status':'GENERALIST_EVALUATION_WRITE_PASS' if a.write else 'GENERALIST_EVALUATION_CHECK_PASS','gates':summary['gates'],'quality':{k:v['quality_counts'] for k,v in summary['profiles'].items()}},indent=2))

if __name__=='__main__':main()
