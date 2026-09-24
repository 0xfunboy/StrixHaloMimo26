"""Materialize a reviewed additive collector/lifecycle overlay before inference."""
from pathlib import Path
import ast
import copy
import difflib
import hashlib
import json
import subprocess
import sys

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
S=ROOT/'sources';OUT=ROOT/'continuity'
sys.path.insert(0,str(S))
from common import atomic,now,sha,read_jsonl,ids_sha


def copy_replace(name,out,edits):
    text=(S/name).read_text();new=text
    for old,replacement in edits:
        if new.count(old)!=1:raise RuntimeError('NON_UNIQUE_SOURCE_EDIT:'+name+':'+old[:60])
        new=new.replace(old,replacement,1)
    ast.parse(new)
    p=S/out
    if p.exists():
        if p.read_text()!=new:raise RuntimeError('EXISTING_ADDENDUM_SOURCE_DIFFERS:'+out)
    else:p.write_text(new)
    (OUT/(out+'.diff')).write_text(''.join(difflib.unified_diff(text.splitlines(True),new.splitlines(True),fromfile=name,tofile=out)))


def main():
    if (OUT/'addendum-SHA256SUMS').exists():raise RuntimeError('ADDENDUM_ALREADY_FROZEN')
    manifest=json.loads((ROOT/'source-manifest.json').read_text())
    for info in manifest['runs'].values():
        if Path(info['run_dir']).exists():raise RuntimeError('MODEL_RUN_ALREADY_EXISTS_NO_NEW_PLAN')
    plan=json.loads((ROOT/'mtp-request-plan.json').read_text())
    primary=read_jsonl(ROOT/'requests-Q.jsonl')
    prose=next(x for x in primary if x['phase']=='benchmark' and x['input_tokens']<4096)
    code=next(x for x in plan if x['case_id']=='MTP-REWRITE-1' and not x['speculation'])
    plans={}
    for side in ['OFF','ON']:
        rows=[copy.deepcopy(x) for x in plan if x['speculation']==(side=='ON')]
        assert len(rows)==6
        for repetition in range(1,4):
            for label,base in [('PROSE',prose),('CODE',code)]:
                item=copy.deepcopy(base)
                item.update(case_id='MTP-PERF-'+label,request_key=f'MTP-PERF-{label}-{repetition}-{side}',phase='mtp_benchmark',
                            output_cap=128,thinking=False,speculation=(side=='ON'),measured=True,timeout_s=1200)
                rows.append(item)
        assert len(rows)==12 and sum(x['output_cap'] for x in rows)==2304
        assert all(x['input_ids_sha256']==ids_sha(x['input_token_ids']) for x in rows)
        plans[side]=rows
    atomic(OUT/'mtp-plan.json',plans)
    copy_replace('adapter_llama.py','adapter_llama_continuity_v1.py',[
        ('from validate import sanity_verdict','from validate import sanity_verdict\nfrom mtp_process_v1 import verify_addendum, collect_off'),
        ("    frozen=verify_freeze(root);manifest=", "    verify_addendum(root)\n    frozen=verify_freeze(root);manifest="),
        ("proc=subprocess.Popen(cfg['command'],stdout=log,stderr=subprocess.STDOUT)","proc=subprocess.Popen(cfg['command'],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'LLAMA_TRACE':'1'})"),
        ("        return 0 if quality=='PASS' else 45", "        if profile=='Q' and quality=='PASS':\n            phase='mtp_off_after_primary_complete'\n            try:collect_off(root,run,base,cfg,proc)\n            except Exception as exc:\n                atomic(run/'mtp-off-blocker.json',{'status':'BLOCKED','phase':phase,'error':type(exc).__name__+':'+str(exc),'primary_records_preserved':len(completed),'at':now()})\n        return 0 if quality=='PASS' else 45")])
    copy_replace('window_guards.py','window_guards_continuity_v1.py',[
        ("    if sha(run/'config.json')!=sha(root/manifest['runs'][cfg['profile']]['config']):raise RuntimeError('CONFIG_FREEZE_MISMATCH')",
         "    from mtp_process_v1 import verify_addendum\n    verify_addendum(root)\n    add=json.loads((root/'continuity/addendum.json').read_text())\n    config_path=add['config_by_run'].get(run.name)\n    if config_path is None or sha(run/'config.json')!=sha(root/config_path):raise RuntimeError('CONFIG_ADDENDUM_MISMATCH')")])
    copy_replace('window_runner.py','window_runner_continuity_v1.py',[
        ('from window_guards import preflight','from window_guards_continuity_v1 import preflight')])
    cfg=copy.deepcopy(json.loads((ROOT/'config-Q.json').read_text()))
    cfg['rank0']['argv'][-1]=str(S/'adapter_llama_continuity_v1.py')
    atomic(OUT/'config-Q.json',cfg)
    mtp_run='generalist-selection-001-QMTP-001';mtp_dir=str(Path(manifest['runs']['Q']['run_dir']).parent/mtp_run)
    mtp_cfg=copy.deepcopy(cfg);mtp_cfg['run_id']=mtp_run;mtp_cfg['rank0']['unit']='mimo26-gs001-qmtp-r0-001'
    mtp_cfg['rank0']['argv']=[x.replace('GS_RUN_DIR='+manifest['runs']['Q']['run_dir'],'GS_RUN_DIR='+mtp_dir) for x in mtp_cfg['rank0']['argv']]
    mtp_cfg['rank0']['argv'][-1]=str(S/'mtp_process_v1.py')
    atomic(OUT/'config-MTP.json',mtp_cfg)
    mtp_meta={'run_id':mtp_run,'run_dir':mtp_dir,'config':'continuity/config-MTP.json','supervisor_unit':'mimo26-gs001-supervisor-qmtp-001.service',
              'supervisor_runtime_s':manifest['runs']['Q']['supervisor_runtime_s'],'supervisor_stop_s':manifest['runs']['Q']['supervisor_stop_s']}
    add={'schema':'strix-generalist-addendum-v1','at':now(),'base_preparation_commit':'87442a8e1b999e5f33165d0b6b563eac5248ab15',
         'base_index_sha256':sha(ROOT/'source-SHA256SUMS'),'authorization':'User continuity integration 2026-09-24; original mandate section 8',
         'config_by_run':{manifest['runs']['Q']['run_id']:'continuity/config-Q.json',mtp_run:'continuity/config-MTP.json'},
         'mtp_run':mtp_meta,'max_additional_model_loads':1,'max_mtp_requests_per_mode':12,'max_mtp_output_tokens_per_mode':2304,
         'primary_32_requests_unchanged':True,'primary_cases_scoring_unchanged':True,'timeouts_unchanged':True,
         'benchmark_input_tokens':{'prose':prose['input_tokens'],'code':code['input_tokens']},
         'benchmark_reference_rule':'OFF preliminary references collected in Q load; eligible only after all six ON equivalence pairs pass. No replacement for any short or mismatching response.',
         'trace_policy':'LLAMA_TRACE=1 in Q and MTP process; existing bounded native verification logs, no GPU profiler; benchmark numbers describe this explicit diagnostic-logging configuration.'}
    atomic(OUT/'addendum.json',add)
    copy_replace('launch.py','launch_continuity_v1.py',[
        ("    prep=json.loads((root/'preparation.json').read_text())",
         "    from mtp_process_v1 import verify_addendum\n    extension=verify_addendum(root)\n    add=json.loads((root/'continuity/addendum.json').read_text())\n    sealed=json.loads((root/'continuity/preparation.json').read_text())\n    if sealed['addendum_index_sha256']!=extension['addendum_index_sha256']:raise RuntimeError('ADDENDUM_PREPARATION_MISMATCH')\n    if profile=='T':\n        qrun=Path(manifest['runs']['Q']['run_dir'])\n        q=json.loads((qrun/'result.json').read_text())\n        off=json.loads((qrun/'mtp-off/summary.json').read_text())\n        if q.get('run_completion')!='PASS' or q.get('cleanup',{}).get('status')!='PASS' or off.get('records')!=12:raise RuntimeError('Q_NOT_QUALIFIED_FOR_MTP')\n        manifest['runs']['T']=add['mtp_run']\n        manifest['profiles']['T']={'status':'ADMITTED'}\n        manifest['order']=manifest['order']+['T']\n    elif profile=='Q':\n        manifest['runs']['Q']['config']='continuity/config-Q.json'\n    prep=json.loads((root/'preparation.json').read_text())"),
        ("str(root/'sources/window_runner.py'),info['run_id']", "str(root/('sources/window_runner_continuity_v1.py' if profile in ('Q','T') else 'sources/window_runner.py')),info['run_id']"),
        ("choices=['Q','M','D','O']", "choices=['Q','M','D','O','T']")])
    print(json.dumps({'status':'APPEND_ONLY_MTP_PLAN_PREPARED','base_files_unchanged':74,'mtp_requests_each':12,'mtp_cap_each':2304,'primary_requests':32,'benchmark_input_tokens':add['benchmark_input_tokens']},indent=2))

if __name__=='__main__': main()
