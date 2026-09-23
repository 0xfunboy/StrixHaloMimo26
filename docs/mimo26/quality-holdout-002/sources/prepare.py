"""CPU preparation and immutable preregistration for HOLDOUT002 only."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from common import atomic,now,sha,ids_sha,read_jsonl
from panel import make_panel

REPO=Path('/home/funboy/StrixHaloMimo26')
ROOT=REPO/'docs/mimo26/quality-holdout-002'
SRC=REPO/'scripts/mimo26/quality_holdout_002'
OLD=REPO/'docs/mimo26/quality-retention-001'
BASE='0e2ae3708beaeec2adf5e993ce2091c2dba4220d'
PEER=Path('/home/funboy/.local/state/strixhalomimo26/quality-holdout-002/frozen')
WINDOWS=Path('/home/funboy/.local/state/strixhalomimo26/windows')
VENV=Path('/home/funboy/StrixHaloClusterGLM/.engine/venv')
MODEL=Path('/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL')


def jsonl(p,rows):
    p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n' for x in rows))


def build():
    assert not (ROOT/'source-SHA256SUMS').exists(),'FROZEN_DO_NOT_REBUILD'
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(str(MODEL),trust_remote_code=True,local_files_only=True)
    cases,expected=make_panel()
    sanity=read_jsonl(OLD/'sanity.jsonl')
    def tokenized(c):
        text=tok.apply_chat_template(c['messages'],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        ids=tok.apply_chat_template(c['messages'],tokenize=True,add_generation_prompt=True,enable_thinking=False)
        if hasattr(ids,'keys'):ids=ids['input_ids']
        if hasattr(ids,'tolist'):ids=ids.tolist()
        if ids and isinstance(ids[0],list):ids=ids[0]
        ids=[int(x) for x in ids]
        assert ids==list(tok.encode(text,add_special_tokens=False)),'TEMPLATE_OR_BOS_MISMATCH'
        assert len(ids)+c['output_cap']+256<=4096,'HARD_CONTEXT_BUDGET:'+c['case_id']
        return {**c,'rendered_text':text,'rendered_text_sha256':hashlib.sha256(text.encode()).hexdigest(),
            'input_token_ids':ids,'input_token_ids_sha256':ids_sha(ids),'input_tokens':len(ids),
            'thinking':False,'add_generation_prompt':True,'tokenizer_add_special_tokens':False}
    cases=[tokenized(c) for c in cases]
    for c in sanity:
        new=tokenized(c)
        assert new['input_token_ids']==c['input_token_ids'] and new['rendered_text']==c['rendered_text'],'SANITY_CHANGED'
    counts=[];targets={'JSON':[800,1800],'EVIDENCE':[1600,2560],'CONSTRAINT':[800,2000]}
    for c,e in zip(cases,expected):
        n=len(tok.encode(json.dumps(e['expected'],ensure_ascii=False),add_special_tokens=False))
        assert n+64<=c['output_cap'],'REFERENCE_TOO_CLOSE_TO_CAP:'+c['case_id']
        e['reference_token_count']=n
        low,high=targets[c['family']]
        counts.append({'case_id':c['case_id'],'family':c['family'],'language':c['language'],'input_tokens':c['input_tokens'],
            'output_cap':c['output_cap'],'reference_tokens':n,'context_with_margin':c['input_tokens']+c['output_cap']+256,
            'indicative_input_target':[low,high],'in_indicative_range':low<=c['input_tokens']<=high,
            'range_note':None if low<=c['input_tokens']<=high else 'Indicative target only; no filler or input truncation used.'})
    jsonl(ROOT/'cases.jsonl',cases);jsonl(ROOT/'expected.jsonl',expected)
    assert (ROOT/'sanity.jsonl').read_bytes()==(OLD/'sanity.jsonl').read_bytes()
    atomic(ROOT/'preflight/tokenization.json',{'status':'PASS','at':now(),'cases':counts,'panel_output_cap_sum':12288,
        'input_min':min(c['input_tokens'] for c in cases),'input_max':max(c['input_tokens'] for c in cases),
        'hard_context_margin':256,'tokenizer_sha256':sha(MODEL/'tokenizer.json'),'template_sha256':sha(MODEL/'chat_template.jinja'),
        'native_runtime_checks':'performed by frozen collectors before requests; CPU template IDs frozen here',
        'no_model_initialization':True})
    print(json.dumps({'status':'CPU_PANEL_PREPARED','cases':counts},indent=2))


def freeze():
    assert not (ROOT/'source-SHA256SUMS').exists(),'FREEZE_ALREADY_EXISTS_RECONCILE'
    for arm in ('A-mixed','B-original'):
        assert not (WINDOWS/('quality-holdout-002-'+arm+'-001')).exists(),'EXISTING_RUN_RECONCILE'
    tests=json.loads((ROOT/'preflight/cpu-tests.json').read_text());assert tests['status']=='PASS'
    prep=json.loads((ROOT/'preflight/tokenization.json').read_text());assert prep['status']=='PASS'
    assert (ROOT/'PROTOCOL.md').exists() and (ROOT/'MANDATE.md').exists(),'PROTOCOL_OR_MANDATE_MISSING'
    subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',BASE,'HEAD'],check=True)
    base=json.loads((OLD/'source-manifest.json').read_text())
    # Verify pinned existing artifacts, not weights or fixtures of closed campaigns.
    for p,h in base['external_lifecycle_hashes'].items():assert sha(p)==h,'RESIDENT_LIFECYCLE_PIN:'+p
    for p,h in base['tokenizer_files'].items():assert sha(p)==h,'TOKENIZER_PIN:'+p
    a=copy.deepcopy(base['runtimes']['A']);b=copy.deepcopy(base['runtimes']['B'])
    assert sha(a['binary']['path'])==a['binary']['sha256']
    for p,h in a['shared_library_hashes'].items():assert sha(p)==h,'A_LIBRARY_PIN:'+p
    for p,h in b['binary_hashes'].items():assert sha(p)==h,'B_LIBRARY_PIN:'+p
    for name,version in b['versions'].items():assert importlib.metadata.version(name)==version,'VERSION_PIN:'+name
    for shard in a['shards_stat_only']:assert Path(shard['path']).stat().st_size==shard['size']
    a['port']=18343;a['command'][a['command'].index('--port')+1]='18343';b['master_port']=29642
    sources=ROOT/'sources';sources.mkdir()
    for p in sorted(SRC.glob('*.py')):shutil.copyfile(p,sources/p.name)
    original=sources/'qualified-001';original.mkdir()
    for name in ('adapter_a.py','adapter_b.py','common.py','validate.py','sandbox_inner.py','launch.py','evaluate.py','prepare.py','window_runner.py','window_cleanup.py','vllm_patch.py'):
        shutil.copyfile(OLD/'sources'/name,original/name)
    for name in ('window_runner.py','window_cleanup.py','vllm_patch.py'):
        shutil.copyfile(OLD/'sources'/name,sources/name)
    assert sha(sources/'vllm_patch.py')==b['patch_sha256']
    for name in ('adapter_a.py','adapter_b.py','sandbox_inner.py'):
        assert (sources/name).read_bytes()==(original/name).read_bytes(),'QUALIFIED_BYTES_CHANGED:'+name
    life=sources/'resident-lifecycle';life.mkdir()
    for p,h in base['external_lifecycle_hashes'].items():shutil.copyfile(p,life/Path(p).name)
    runs={}
    for arm,label,work in [('A','A-mixed',7200),('B','B-original',14400)]:
        cfg=copy.deepcopy(json.loads((OLD/('config-'+arm+'.json')).read_text()))
        shutil.copyfile(OLD/('config-'+arm+'.json'),original/('config-'+arm+'.json'))
        run_id='quality-holdout-002-'+label+'-001';run=WINDOWS/run_id
        cfg.update(schema='mimo26-quality-holdout-window-v1',campaign='QUALITY-HOLDOUT-002',run_id=run_id,arm=arm,
            work_timeout_sec=work,worker_runtime_sec=work+120,quiesce_timeout_sec=720,restore_timeout_sec=1200)
        for rank in (0,1):
            w=cfg.get('rank'+str(rank))
            if not w:continue
            nr=ROOT if rank==0 else PEER
            replacements={str(OLD):str(ROOT),'/home/funboy/.local/state/strixhalomimo26/quality-retention-001/frozen':str(PEER),
                str(WINDOWS/('quality-retention-001-'+label+'-001')):str(run),'--master-port=29641':'--master-port=29642'}
            argv=[]
            for item in w['argv']:
                for before,after in replacements.items():item=item.replace(before,after)
                argv.append(item)
            w['argv']=argv;w['unit']=f'mimo26-qh002-{arm.lower()}-r{rank}-001'
            assert any(x=='QR_ROOT='+str(nr) for x in argv)
            assert any(x=='QR_RUN_DIR='+str(run) for x in argv)
        atomic(ROOT/('config-'+arm+'.json'),cfg)
        runs[arm]={'run_id':run_id,'run_dir':str(run),'supervisor_unit':f'mimo26-qh002-supervisor-{arm.lower()}-001.service',
            'supervisor_runtime_s':work+2040,'supervisor_stop_s':1200,'config':'config-'+arm+'.json'}
    manifest={'schema':'mimo26-holdout-preregistration-v1','campaign':'QUALITY-HOLDOUT-002','frozen_at':now(),'base_commit':BASE,
        'entry_commit':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        'base_001_manifest_sha256':sha(OLD/'source-manifest.json'),'models':base['models'],'runtimes':{'A':a,'B':b},
        'runs':runs,'arm_order':['A','RESTORE','B','RESTORE'],'case_order':[x['case_id'] for x in read_jsonl(ROOT/'cases.jsonl')],
        'panel_cases_per_arm':18,'sanity_per_phase':6,'planned_primary_records_per_arm':30,'panel_output_cap_total_per_arm':12288,
        'sampling':base['sampling'],'input_contract':base['input_contract'],'context_contract':{'size':4096,'additional_margin':256,'automatic_truncation':False},
        'timeout_contract':{'A_work_s':7200,'B_work_s':14400,'restore_s':1200,'per_case':'output cap/2 +240 seconds (496 or752); sanity300',
            'planning_basis':'conservative 2 output tokens/s for cap12288 plus prompt allowance, load and12 sanity, finite margin; not a performance result',
            'supervisor':'qualified001 runner/cleanup byte-identical, finite transient unit bounds frozen before both runs'},
        'sandbox':base['sandbox'],'external_lifecycle_hashes':base['external_lifecycle_hashes'],'restore':base['restore'],
        'tokenizer_files':base['tokenizer_files'],'peer_root':str(PEER),'cpu_tests':{'path':'preflight/cpu-tests.json','sha256':sha(ROOT/'preflight/cpu-tests.json')},
        'freeze_role':'PREREGISTRATION_BEFORE_ANY_HOLDOUT_GPU_LOAD','closed_campaigns':'QR001 and PERF001 immutable, no benchmarks/recovery reopened',
        'evaluation':'independent literal JSON references, claim-specific citation sufficiency sets, dual exact constraint oracles; no model judge',
        'selection_bias':'new instances; families selected using known001 failures; not blind representative sample',
        'decision_contract':'per-family scoped proposal only; no promotion threshold, deployment, follow-on experiment or repair',
        'source_adaptations':{'adapters':'A/B exact001 bytes; runtime configs loaded from new manifest','common':'campaign ID, atomic no-replace publication and loaded-module path/hash proof',
            'validate':'qualified001 sanity validator; unique sandbox container prefix','launch':'campaign/path/port and18-case prerequisites only'},
        'original_collectors_archived':'sources/qualified-001/','mandate_provenance_sha256':sha(ROOT/'MANDATE.md'),'mandate_attachment_sha256':'b73f9233798296a75f457dd03acb64c4de9aa423c09f107d9e5e00c464e58431'}
    atomic(ROOT/'source-manifest.json',manifest)
    files=[ROOT/p for p in ('MANDATE.md','PROTOCOL.md','cases.jsonl','expected.jsonl','sanity.jsonl','source-manifest.json','config-A.json','config-B.json','preflight/cpu-tests.json','preflight/tokenization.json')]
    files.extend(p for p in sources.rglob('*') if p.is_file())
    files=sorted(files)
    (ROOT/'source-SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(ROOT))+'\n' for p in files))
    print(json.dumps({'status':'HOLDOUT_SOURCES_FROZEN','files':len(files),'index_sha256':sha(ROOT/'source-SHA256SUMS'),'at':manifest['frozen_at']}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','freeze']);args=p.parse_args()
    (build if args.action=='build' else freeze)()
