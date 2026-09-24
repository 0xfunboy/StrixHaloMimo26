"""Freeze complete tested source bytes and isolated configurations before any window."""
from __future__ import annotations
import argparse
import ast
import difflib
import json
from pathlib import Path
import shutil
import subprocess
from common import atomic,now,sha

REPO=Path('/home/funboy/StrixHaloMimo26');ROOT=REPO/'docs/selection/strix-generalist-selection-001'
CODE=REPO/'scripts/selection/generalist001';BASE=Path('/home/funboy/ai-exp/strix-generalist-selection-001')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT);args=ap.parse_args();root=args.root.resolve()
    if (root/'source-SHA256SUMS').exists():raise RuntimeError('FREEZE_EXISTS_RECONCILE_DO_NOT_REWRITE')
    for name in ['cpu-tests-final.json','adapter-lifecycle-tests-final.json','runtime-options.json','tokenization.json','gguf-inventory.json','e1-gguf-inventory.json','mtp-mapping.json','acquire-weights.json']:
        data=json.loads((root/'preflight'/name).read_text())
        if data.get('status')!='PASS':raise RuntimeError('PREFLIGHT_NOT_PASS:'+name)
    manifest=json.loads((root/'source-manifest.json').read_text())
    if manifest['status']!='DRAFT_NOT_FROZEN':raise RuntimeError('UNEXPECTED_MANIFEST_PHASE')
    plans={p:[json.loads(x) for x in (root/('requests-'+p+'.jsonl')).read_text().splitlines()] for p in manifest['order']}
    for profile,rows in plans.items():
        assert len(rows)==32 and sum(x['phase']=='panel' for x in rows)==12
        assert sum(x['output_cap'] for x in rows if x['phase']=='panel')==73728
        assert all(x['input_tokens']+x['output_cap']+256<=16384 for x in rows)
    for a,b in zip(plans['M'],plans['O']):assert a['input_token_ids']==b['input_token_ids'] and a['rendered_text']==b['rendered_text']
    entry=json.loads((root/'preflight/entry.json').read_text())
    preservation=[]
    for group in ['closed_campaign_files','preexisting_scratch']:
        for item in entry[group]:
            if not isinstance(item,dict):raise TypeError('entry inventory structure changed')
            p=Path(item['path'])
            if not p.exists() or sha(p)!=item['sha256']:raise RuntimeError('PRESERVED_SOURCE_CHANGED:'+str(p))
        preservation.append({'group':group,'files_unchanged':len(entry[group])})
    actual=subprocess.check_output(['git','-C',str(BASE/'qwen-runtime'),'rev-parse','HEAD'],text=True).strip()
    assert actual==manifest['profiles']['Q']['runtime_revision']
    diff=subprocess.check_output(['git','-C',str(BASE/'qwen-runtime'),'diff','--binary'],text=True)
    assert not diff,'QWEN_NUMERIC_SOURCE_CHANGED'
    acquisition=json.loads((root/'preflight/acquire-weights.json').read_text())
    for item in acquisition['files']:
        p=Path(item['destination'])
        assert p.stat().st_size==item['size'] and item['status'] in ('VERIFIED','EXISTING_VERIFIED')
    import os
    free=os.statvfs('/home/funboy').f_bavail*os.statvfs('/home/funboy').f_frsize
    assert free>=60*2**30,'FREE_SPACE_GATE_BEFORE_WINDOWS'
    sources=root/'sources';sources.mkdir(exist_ok=False)
    for p in sorted(CODE.glob('*.py')):
        ast.parse(p.read_text());shutil.copyfile(p,sources/p.name)
    tooling=root/'tooling-source';tooling.mkdir(exist_ok=False)
    for p in sorted((REPO/'scripts/selection').glob('generalist001_*.py')):
        shutil.copyfile(p,tooling/p.name)
    for name in ['window_runner.py','window_cleanup.py','adapter_a.py','adapter_b.py']:
        old=root/'qualified-002'/name
        current=sources/name if name in ['window_runner.py','window_cleanup.py'] else sources/('adapter_llama.py' if name=='adapter_a.py' else 'adapter_original.py')
        (root/'preflight'/('diff-'+name+'.patch')).write_text(''.join(difflib.unified_diff(old.read_text().splitlines(True),current.read_text().splitlines(True),fromfile='qualified-002/'+name,tofile='sources/'+current.name)))
    lifecycle=sources/'resident-lifecycle';lifecycle.mkdir()
    for source,h in manifest['resident_lifecycle_hashes'].items():
        assert sha(source)==h;shutil.copyfile(source,lifecycle/Path(source).name)
    inventory=json.loads((root/'preflight/gguf-inventory.json').read_text())
    for profile,prefix in [('Q','trunk-q5k-'),('M','MiMo-V2.6-Flash-RL-MQ-')]:
        selected=[x for x in inventory['files'] if Path(x['path']).name.startswith(prefix)]
        manifest['profiles'][profile]['model_inventory']=[{'path':x['path'],'bytes':x['bytes'],'families':x['families']} for x in selected]
        manifest['profiles'][profile]['status']='ADMITTED'
    dinv=json.loads((root/'preflight/e1-gguf-inventory.json').read_text());manifest['profiles']['D']['model_families']=dinv['families'];manifest['profiles']['D']['model_metadata']=dinv['metadata']
    original=json.loads(Path('/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL/config.json').read_text())
    manifest['profiles']['O']['quantization_config']=original.get('quantization_config',original.get('text_config',{}).get('quantization_config'))
    manifest.update(status='FROZEN_BEFORE_MODELS',frozen_at=now(),source_completeness='Complete bytes of own executed tools and qualified base copies retained; external runtimes pinned with existing full source checkout/archive and binary hashes.',
                    artifact_acquisition='preflight/acquire-weights.json',preflight_preservation=preservation,free_bytes_before_windows=free,
                    cpu_tests={'main':'preflight/cpu-tests-final.json','contracts':'preflight/adapter-lifecycle-tests-final.json'})
    atomic(root/'source-manifest.json',manifest)
    files=[root/x for x in ['PROTOCOL.md','MANDATE_SOURCE.md','source-manifest.json','cases.jsonl','expected.jsonl','engine-documents.json','mtp-cases.json','mtp-request-plan.json']]
    files+=[root/('requests-'+p+'.jsonl') for p in manifest['order']]+[root/('config-'+p+'.json') for p in manifest['order']]
    for directory in ['sources','tooling-source','qualified-002','tokenizers']:
        files.extend(p for p in (root/directory).rglob('*') if p.is_file())
    for name in ['cpu-tests-final.json','adapter-lifecycle-tests-final.json','runtime-options.json','tokenization.json','gguf-inventory.json','e1-gguf-inventory.json','mtp-mapping.json','acquire-weights.json']:
        files.append(root/'preflight'/name)
    files=sorted(set(files));assert all(p.exists() for p in files)
    with (root/'source-SHA256SUMS').open('x') as f:
        for p in files:f.write(sha(p)+'  '+str(p.relative_to(root))+'\n')
    atomic(root/'registry.json',{'campaign':manifest['campaign'],'phase':'FROZEN_PENDING_PREPARATION_COMMIT','at':now(),'source_index_sha256':sha(root/'source-SHA256SUMS'),
        'models_started':False,'next_exact_action':'Commit only the prepared selection files, record preparation.json, verify peer frozen bytes, then launch Q through the frozen supervisor.'})
    (root/'HANDOFF.md').write_text('# STRIX-GENERALIST-SELECTION-001\n\nPHASE: FROZEN_PENDING_PREPARATION_COMMIT\nBASE: '+manifest['base_commit']+'\nSOURCE_INDEX_SHA256: '+sha(root/'source-SHA256SUMS')+'\n\nNo model window has started. Qwen build and selected acquisition PASS; twelve independent cases and CPU adapter/lifecycle tests PASS. MTP remains BLOCKED_STATIC_CONTROL_CONTRACT; four target profiles proceed spec OFF. K2 is the saved resident, not E1. Read registry/source-manifest before any dispatch.\n\nNEXT: local preparation commit, preparation receipt and peer source verification, then Q via sources/launch.py. Preserve all prior campaigns and scratch. No replay, push or deployment.\n')
    print(json.dumps({'status':'SOURCE_FREEZE_PASS','files':len(files),'index_sha256':sha(root/'source-SHA256SUMS'),'models_started':False,'preservation':preservation},indent=2))

if __name__=='__main__':main()
