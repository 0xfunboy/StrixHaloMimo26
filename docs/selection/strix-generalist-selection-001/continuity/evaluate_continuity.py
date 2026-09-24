"""CPU delivery for the preregistered continuity overlay; original scoring unchanged."""
from __future__ import annotations
import argparse
import collections
import copy
import json
from pathlib import Path
import re
import sys

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
sys.path.insert(0,str(ROOT/'sources'))
import evaluate as original
from common import digest,read_jsonl,sha
from mtp_process_v1 import compare_pair,metrics,verify_addendum
from d_readiness_recovery_v1 import effective_manifest,verify_recovery

BASE_LOAD_PROFILE=original.load_profile


def effective_load_profile(root,manifest,profile):
    effective=copy.deepcopy(manifest)
    if profile=='Q':effective['runs']['Q']['config']='continuity/config-Q.json'
    recovered_D=profile=='D' and (root/'recovery-D/preparation.json').exists()
    if recovered_D:effective=effective_manifest(root,effective)
    values,meta,records=BASE_LOAD_PROFILE(root,effective,profile)
    if (profile=='Q' or recovered_D) and meta['load'].get('status')=='PASS':
        receipt=verify_recovery(root) if recovered_D else verify_addendum(root)
        actual=meta['load'].get('source_freeze',{}).get('loaded_modules',{}).get('__main__',{})
        expected=root/('sources/adapter_ds41_readiness_v1.py' if recovered_D else 'sources/adapter_llama_continuity_v1.py')
        certified=(actual.get('path')==str(expected.resolve()) and actual.get('sha256')==sha(expected))
        # This is the pre-output authorized adapter name change, not a scoring exception.
        name='runtime frozen import mismatch:__main__'
        if certified:
            meta['original_adapter_name_warning']=name if name in meta['issues'] else None
            meta['issues']=[x for x in meta['issues'] if x!=name]
            meta['effective_adapter_attestation']={'status':'PASS','actual':actual,'supplement_index_sha256':receipt['recovery_index_sha256'] if recovered_D else receipt['addendum_index_sha256']}
        else:meta['issues'].append('continuity adapter attestation mismatch')
        meta['effective_config']=effective['runs'][profile]['config']
        meta['runtime_qualification']='PASS' if certified and not meta['issues'] and all(x['status']=='PASS' for x in meta['sanity'].values()) else 'NOT_QUALIFIED_OR_INCOMPLETE'
    if recovered_D:
        prior=json.loads((root/'recovery-D/manifest.json').read_text())['prior_run'];path=Path(prior['run_dir'])
        result=json.loads((path/'result.json').read_text())
        no_requests=not (path/'requests').exists() and not (path/'raw-results.jsonl').exists()
        if not no_requests:meta['issues'].append('unexpected prior D request; cannot treat as packaging-only recovery')
        meta['preserved_setup_attempt']={'run_id':prior['run_id'],'run_dir':str(path),'result_sha256':sha(path/'result.json'),
            'run_completion':result.get('run_completion'),'cleanup':result.get('cleanup'),'zero_requests_verified':no_requests,
            'evidence':'recovery-D/setup-evidence.json','source_receipt':json.loads((root/'recovery-D/preparation.json').read_text())}
        meta['total_model_launch_attempts_including_setup']=meta['launch_count']+int((path/'launch-count.txt').read_text())
        if not no_requests:meta['runtime_qualification']='NOT_QUALIFIED_OR_INCOMPLETE'
    return values,meta,records


def audit_mtp_side(root,run,side,plans):
    sub=run/('mtp-'+side.lower());path=sub/'raw-results.jsonl'
    rows=read_jsonl(path) if path.exists() else [];issues=[]
    expected=[(x['phase'],x['request_key']) for x in plans]
    actual=[(x.get('phase'),x.get('request_key')) for x in rows]
    if actual!=expected[:len(actual)]:issues.append('order or repeated request')
    if len(set(actual))!=len(actual):issues.append('duplicate request')
    for rec,plan in zip(rows,plans):
        key=plan['request_key'];dest=sub/'requests'/(plan['phase']+'__'+key)
        if rec.get('record_sha256')!=digest({k:v for k,v in rec.items() if k!='record_sha256'}):issues.append(key+': digest')
        if json.loads((dest/'result.json').read_text())!=rec:issues.append(key+': atomic copy')
        for field in ['messages','rendered_text','input_token_ids','input_ids_sha256','output_cap','thinking','sampling','timeout_s']:
            if rec.get(field)!=plan[field]:issues.append(key+': '+field)
        if rec.get('completion_status') in ['TECHNICAL_ERROR','TIMEOUT']:
            issues.append(key+': '+rec['completion_status']);continue
        native=json.loads((dest/'native-response.json').read_text());n=rec.get('output_tokens')
        if native!=rec.get('native_response') or native.get('tokens')!=rec.get('output_token_ids') or len(native.get('tokens',[]))!=n:issues.append(key+': native output')
        tm=native.get('timings',{})
        if tm.get('cache_n')!=0 or tm.get('prompt_n')!=len(plan['input_token_ids']) or tm.get('predicted_n')!=n:issues.append(key+': cache/count')
        before=metrics((dest/'metrics-before.txt').read_text());after=metrics((dest/'metrics-after.txt').read_text())
        delta={k:v-before.get(k,0) for k,v in after.items()}
        if delta!=rec.get('metrics_delta') or any(v<0 for v in delta.values()):issues.append(key+': metrics')
        draft=delta.get('llamacpp:spec_decode_num_draft_tokens_total');accept=delta.get('llamacpp:spec_decode_num_accepted_tokens_total')
        if draft is None or accept is None or not 0<=accept<=draft or (side=='OFF' and draft!=0):issues.append(key+': draft counters')
        steps=[{'accepted':int(a),'drafted':int(b)} for a,b in re.findall(r'accepted\s+(\d+)\s*/\s*(\d+) draft tokens',(dest/'native-trace.log').read_text())]
        if rec.get('acceptance_steps')!=steps or rec.get('partial_acceptance_observed')!=any(0<s['accepted']<s['drafted'] for s in steps):issues.append(key+': partial acceptance evidence')
    return rows,issues


def mtp_summary(root,primary):
    add=json.loads((root/'continuity/addendum.json').read_text())
    plans=json.loads((root/'continuity/mtp-plan.json').read_text())
    qr=Path(primary['profiles']['Q']['run_dir']);tr=Path(add['mtp_run']['run_dir'])
    off,off_errors=audit_mtp_side(root,qr,'OFF',plans['OFF']);on,on_errors=audit_mtp_side(root,tr,'ON',plans['ON'])
    byoff={r['case_id']:r for r in off if r['phase']=='mtp_equivalence'}
    pairs=[]
    for rec in on:
        if rec['phase']=='mtp_equivalence' and rec['case_id'] in byoff and rec.get('completion_status') not in ('TECHNICAL_ERROR','TIMEOUT'):
            pairs.append(compare_pair(byoff[rec['case_id']],rec))
    state=json.loads((tr/'result.json').read_text()) if (tr/'result.json').exists() else {}
    exact=len(pairs)==6 and all(p['status']=='PASS' for p in pairs)
    active=any(r.get('draft_tokens',0)>0 for r in on)
    partial=any(r.get('partial_acceptance_observed') for r in on if r['phase']=='mtp_equivalence')
    if off_errors or on_errors:status='BLOCKED_COLLECTOR_OR_NATIVE_CONTRACT'
    elif not on and (qr/'mtp-off-blocker.json').exists():status='BLOCKED_OFF_REFERENCE_COLLECTOR'
    elif not on:status='NOT_RUN'
    elif len(pairs)<6:status='INCOMPLETE_EQUIVALENCE'
    elif not exact:status='FAIL_GREEDY_EQUIVALENCE'
    elif not (partial and active):status='INCOMPLETE_STATE_BRANCH_NOT_EXERCISED'
    else:status='GREEDY_EQUIVALENCE_AND_PARTIAL_REJECTION_PASS'
    admitted=status=='GREEDY_EQUIVALENCE_AND_PARTIAL_REJECTION_PASS'
    bench={}
    for case_id in ('MTP-PERF-PROSE','MTP-PERF-CODE'):
        row={}
        for side,records in [('OFF',off),('ON',on)]:
            group=[r for r in records if r['phase']=='mtp_benchmark' and r['case_id']==case_id]
            valid=[r for r in group if r.get('completion_status')=='VALID_CAP']
            row[side]={'count':len(group),'n_valid':len(valid),'decode_tps':original.stats((r.get('engine_metrics') or {}).get('decode_engine_tps') for r in valid),
                       'request_seconds':original.stats(r.get('request_latency_s') for r in valid),
                       'samples':[{'request_id':r['request_id'],'status':r['completion_status'],'input_tokens':r['input_tokens'],'output_tokens':r.get('output_tokens'),'seconds':r.get('request_latency_s'),'timings':r.get('engine_metrics'),'draft':r.get('draft_tokens'),'accepted':r.get('accepted_tokens')} for r in group]}
        a=row['OFF']['decode_tps']['median'];b=row['ON']['decode_tps']['median']
        row['qualified_ratio']=b/a if admitted and row['OFF']['n_valid']==row['ON']['n_valid']==3 and a and b else None
        row['admitted']=admitted;bench[case_id]=row
    blockers={}
    for label,path in [('OFF',qr/'mtp-off-blocker.json'),('ON',tr/'fatal.json')]:
        if path.exists():blockers[label]=json.loads(path.read_text())
    return {'status':status,'supersedes':'Original manifest static HTTP-toggle blocker only; process-level addendum preregistered before Q.',
            'OFF_records':len(off),'ON_records':len(on),'OFF_errors':off_errors,'ON_errors':on_errors,'pairs':pairs,'partial_acceptance_observed':partial,
            'drafting_observed':active,'sampled_distribution_equivalence':'NOT_ESTABLISHED','run':str(tr),'run_completion':state.get('run_completion','NOT_STARTED'),
            'restore':state.get('cleanup'),'benchmarks':bench,'blockers':blockers,'additional_model_loads':int((tr/'launch-count.txt').read_text()) if (tr/'launch-count.txt').exists() else 0}


def compute(root):
    extension=verify_addendum(root)
    original.load_profile=effective_load_profile
    try:summary,raw=original.compute(root)
    finally:original.load_profile=BASE_LOAD_PROFILE
    summary['original_frozen_mtp_statement']=summary['mtp']
    summary['mtp']=mtp_summary(root,summary);summary['gates']['MTP']=summary['mtp']['status']
    summary['continuity']={'base_index_sha256':extension['base']['index_sha256'],'addendum_index_sha256':extension['addendum_index_sha256'],
                           'preparation':json.loads((root/'continuity/preparation.json').read_text()),
                           'scoring':'Original frozen verdict/record audit unchanged. Only authorized Q config/adapter attestation and the separately preregistered process MTP are reconciled.',
                           'historical_evidence':'QWEN_HISTORY_AND_REUSE.md; historical scores are not pooled into this campaign.'}
    return summary,raw


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--write',action='store_true');p.add_argument('--check',action='store_true');a=p.parse_args()
    if a.write==a.check:p.error('choose --write or --check')
    root=a.root.resolve();summary,raw=compute(root)
    files=original.outputs(summary,raw)
    report=files['REPORT.md'].replace('sources/evaluate.py','continuity/evaluate_continuity.py').replace('PYTHONDONTWRITEBYTECODE=1 python3','PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 python3')
    report+='\n## Continuity attestation\n\nThe original 74-file freeze and the pre-output 15-file addendum are separate and preserved. The Q adapter and process configuration were authorized and frozen in the addendum, not a post-output scoring change. Historical Qwen reports were recovered without rerunning the old tests.\n'
    files['REPORT.md']=report
    for name,text in files.items():
        path=root/name
        if a.write:path.write_text(text)
        elif path.read_text()!=text:raise AssertionError('CPU_RECALCULATION_MISMATCH:'+name)
    print(json.dumps({'status':'CONTINUITY_EVALUATION_WRITE_PASS' if a.write else 'CONTINUITY_EVALUATION_CHECK_PASS','gates':summary['gates'],
                      'quality':{k:v['quality_counts'] for k,v in summary['profiles'].items()},'issues':{k:v['issues'] for k,v in summary['profiles'].items()}},indent=2))

if __name__=='__main__':main()
