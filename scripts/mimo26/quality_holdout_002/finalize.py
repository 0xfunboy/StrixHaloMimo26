"""Post-window receipts, immutable evidence copies and local delivery; no inference dispatch."""
from __future__ import annotations
import argparse
import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from common import atomic,now,sha,verify_freeze,read_jsonl
from launch import SSH,unit_status,controller

REPO=Path('/home/funboy/StrixHaloMimo26')
ROOT=REPO/'docs/mimo26/quality-holdout-002'


def cmd(args,timeout=30):return subprocess.check_output([str(a) for a in args],text=True,timeout=timeout)


def process_snapshot():
    code="""import json,os
from pathlib import Path
rows=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  name=(p/'comm').read_text().strip()
  if name.startswith('VLLM') or name.startswith('llama-server'):
   rows.append({'pid':int(p.name),'name':name,'cgroup':(p/'cgroup').read_text().strip()})
 except (OSError,ProcessLookupError):pass
print(json.dumps(rows))
"""
    return {'NODE01':json.loads(cmd(['/usr/bin/python3','-c',code])),
        'NODE02':json.loads(cmd(SSH+[shlex.join(['/usr/bin/python3','-c',code])]))}


def snapshot(arm=None,filename=None):
    m=json.loads((ROOT/'source-manifest.json').read_text());st=controller(m)
    arms=[arm] if arm else ['A','B'];observed=now()
    identities={'NODE01':cmd(['bash','-c','hostname; id -un; cat /proc/sys/kernel/random/boot_id']).splitlines(),
        'NODE02':cmd(SSH+['hostname; id -un; cat /proc/sys/kernel/random/boot_id']).splitlines()}
    assert identities['NODE01'][:2]==['01-EVO-X3','funboy'] and identities['NODE02'][:2]==['02-EVO-X3','funboy']
    assert st['state']=='READY' and st['owner']=='DS41' and st['owner_state']=='RUNNING'
    assert st['release_id']==m['restore']['release_id'] and st['preset']==m['restore']['preset']
    owner=json.loads(Path('/home/funboy/.local/state/strix-cluster/owner.json').read_text())
    resident={str(i):unit_status('ds41-rank'+str(i)+'.service',peer=i==1) for i in (0,1)}
    for i in (0,1):assert resident[str(i)]['ActiveState']=='active' and resident[str(i)]['InvocationID']==owner['ranks'][str(i)]['invocation_id']
    own_units={};original_pids={};native_restores={}
    for a in arms:
        spec=m['runs'][a];run=Path(spec['run_dir']);cfg=json.loads((run/'config.json').read_text());result=json.loads((run/'result.json').read_text())
        assert result['run_completion']=='PASS' and result['cleanup']['status']=='PASS'
        assert int((run/'launch-count.txt').read_text())==1
        own_units[spec['supervisor_unit']]=unit_status(spec['supervisor_unit'])
        for rank in (0,1):
            w=cfg.get('rank'+str(rank))
            if w:own_units[('NODE02:' if rank==1 else '')+w['unit']]=unit_status(w['unit'],peer=rank==1)
        load=json.loads((run/'load.json').read_text());pids=[('NODE01',load['pid'])]
        if a=='B':
            peerload=json.loads(cmd(SSH+['cat '+shlex.quote(str(run/'load-rank1.json'))]));pids.append(('NODE02',peerload['pid']))
        for node,pid in pids:
            probe=f'test -d /proc/{int(pid)} && echo PRESENT || echo ABSENT'
            state=cmd(SSH+[probe] if node=='NODE02' else ['bash','-c',probe]).strip()
            original_pids[f'{a}:{node}:{pid}']=state
            assert state=='ABSENT','ORIGINAL_MODEL_PID_STILL_PRESENT'
        after=json.loads((run/'k2-after.json').read_text());assert after['state']=='READY' and after['release_id']==m['restore']['release_id']
        native_restores[a]={'cleanup':result['cleanup'],'controller':after}
    for name,u in own_units.items():assert u['ActiveState'] not in ('active','activating','deactivating') and u['MainPID']=='0','OWNED_UNIT_NOT_TERMINAL:'+name
    locks=cmd(['lslocks','--noheadings','-o','PID,COMMAND,PATH'])
    relevant=[line for line in locks.splitlines() if '/strix-cluster/compute.lock' in line or '/strixhalomimo26/cleanup-global.lock' in line or 'quality-holdout-002' in line]
    assert not relevant,'RELEVANT_LOCK_HELD'
    engines=process_snapshot()
    assert not any('mimo26-qh002' in p['cgroup'] or 'quality-holdout-002' in p['cgroup'] for rows in engines.values() for p in rows),'OWNED_ENGINE_RESIDUE'
    receipt={'schema':'mimo26-holdout-live-v1','status':'PASS','observation_started_at':observed,'observation_completed_at':now(),
        'identities':identities,'controller':st,'owner':{'owner':owner['owner'],'state':owner['state'],'epoch':owner['epoch'],
            'rank_invocations':{k:v['invocation_id'] for k,v in owner['ranks'].items()}},'resident_units':resident,
        'own_units':own_units,'original_model_pid_absence':original_pids,'matching_lock_holders':relevant,
        'remaining_engine_cgroups':engines,'historical_restores':native_restores,'note':'EngineCore in DS41 cgroups are restored residents, not MiMo residue. Read-only checks, no new generations or lifecycle transitions.'}
    target=ROOT/(filename or ('restore-'+arm+'.json' if arm else 'final-live.json'))
    if target.exists():
        raise RuntimeError('SNAPSHOT_ALREADY_EXISTS_USE_DISTINCT_DELIVERY_FILENAME')
    atomic(target,receipt,exclusive=True)
    print(json.dumps({'status':'LIVE_RESTORE_RECEIPT_PASS','path':str(target),'at':receipt['observation_completed_at'],'controller':st},indent=2))


def archive():
    m=json.loads((ROOT/'source-manifest.json').read_text());evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
    verify_freeze(ROOT)
    assert json.loads((ROOT/'final-live.json').read_text())['status']=='PASS'
    peer_run=Path(m['runs']['B']['run_dir'])
    peer_source=str(peer_run/'rank1-raw-results.jsonl')
    remote_hash=cmd(SSH+['sha256sum '+shlex.quote(peer_source)]).split()[0]
    data=subprocess.check_output(SSH+['cat '+shlex.quote(peer_source)],timeout=30)
    import hashlib
    assert hashlib.sha256(data).hexdigest()==remote_hash
    target=evidence/'B-rank1-raw-results.jsonl'
    if target.exists():assert target.read_bytes()==data,'PEER_COPY_CONFLICT'
    else:target.write_bytes(data)
    receipt={'node':'02-EVO-X3','source':peer_source,'sha256':remote_hash,'at':now(),'record_count':len(data.splitlines())}
    atomic(evidence/'peer-copy-receipt.json',receipt)
    files=[]
    for arm in ('A','B'):
        run=Path(m['runs'][arm]['run_dir']);assert unit_status(m['runs'][arm]['supervisor_unit'])['ActiveState']=='inactive'
        for p in sorted(run.rglob('*')):
            if not p.is_file() or p.name in ('run.lock','compute-lock-held') or '.tmp-' in p.name:continue
            assert not p.is_symlink()
            dest=evidence/('run-'+arm)/p.relative_to(run);dest.parent.mkdir(parents=True,exist_ok=True)
            h=sha(p)
            if dest.exists():assert sha(dest)==h,'ARCHIVE_CONFLICT:'+str(dest)
            else:shutil.copyfile(p,dest)
            assert sha(p)==sha(dest)==h,'SOURCE_CHANGED_DURING_ARCHIVE'
            files.append({'source':str(p),'copy':str(dest.relative_to(ROOT)),'sha256':h,'bytes':p.stat().st_size})
    # Preserve rank1 diagnostics and native ID checks without counting extra samples.
    peer_extra=[]
    for name in ('load-rank1.json','input-checks-rank1.json','arm-result-rank1.json','rank1.log'):
        source=str(peer_run/name);h=cmd(SSH+['sha256sum '+shlex.quote(source)]).split()[0];body=subprocess.check_output(SSH+['cat '+shlex.quote(source)],timeout=30)
        assert hashlib.sha256(body).hexdigest()==h
        dest=evidence/'NODE02'/name;dest.parent.mkdir(exist_ok=True)
        if dest.exists():assert dest.read_bytes()==body
        else:dest.write_bytes(body)
        peer_extra.append({'node':'02-EVO-X3','source':source,'copy':str(dest.relative_to(ROOT)),'sha256':h,'bytes':len(body)})
    peer_inputs=json.loads((evidence/'NODE02/input-checks-rank1.json').read_text())
    for c in read_jsonl(ROOT/'cases.jsonl')+read_jsonl(ROOT/'sanity.jsonl'):
        check=peer_inputs[c['case_id']];assert check['ids_match'] and check['rendered_match'] and check['actual_token_ids']==c['input_token_ids']
    atomic(evidence/'archive-manifest.json',{'status':'PASS','at':now(),'source_unchanged':True,'files':files,'peer_files':peer_extra,'peer_raw':receipt})
    (evidence/'original-SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['source']+'\n' for x in files))
    print(json.dumps({'status':'EVIDENCE_ARCHIVE_PASS','node01_files':len(files),'peer_extra_files':len(peer_extra),'peer_records':len(data.splitlines())}))


def verify():
    m=json.loads((ROOT/'source-manifest.json').read_text());freeze=verify_freeze(ROOT)
    summary=json.loads((ROOT/'summary.json').read_text())
    result=subprocess.run(['/usr/bin/python3',str(ROOT/'sources/evaluate.py'),'--root',str(ROOT),'--check'],text=True,capture_output=True,timeout=90,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    vdir=ROOT/'verification';vdir.mkdir(exist_ok=True)
    (vdir/'evaluation-check.stdout').write_text(result.stdout);(vdir/'evaluation-check.stderr').write_text(result.stderr)
    assert result.returncode==0,result.stdout+result.stderr
    entry=json.loads((ROOT/'preflight/entry.json').read_text());closed=[]
    for name,index in entry['closed_campaign_files'].items():
        for p,h in index.items():assert sha(REPO/p)==h,'CLOSED_CAMPAIGN_CHANGED:'+p
        closed.append({'campaign':name,'files_unchanged':len(index)})
    for p,h in entry['scratch_files'].items():assert sha(REPO/p)==h,'PREEXISTING_SCRATCH_CHANGED:'+p
    archive=json.loads((ROOT/'evidence/archive-manifest.json').read_text())
    for f in archive['files']:assert sha(f['source'])==sha(ROOT/f['copy'])==f['sha256'],'RAW_CHANGED:'+f['source']
    for p,h in m['external_lifecycle_hashes'].items():assert sha(p)==h,'RESIDENT_SOURCE_CHANGED'
    peer_index=cmd(SSH+['cd '+shlex.quote(m['peer_root'])+' && sha256sum -c source-SHA256SUMS'])
    verification={'status':'PASS','at':now(),'CPU_RECALCULATION_CHECK':'PASS','source_freeze':freeze,'original_files_unchanged':len(archive['files']),
        'closed_campaigns_unchanged':closed,'preexisting_scratch_files_unchanged':len(entry['scratch_files']),
        'peer_freeze_files_checked':len(peer_index.splitlines()),'resident_sources_unchanged':True,
        'command':'PYTHONDONTWRITEBYTECODE=1 python3 docs/mimo26/quality-holdout-002/sources/evaluate.py --root docs/mimo26/quality-holdout-002 --check',
        'dependencies':'original paths on NODE01 and pinned existing Podman image for sanity; no model inference'}
    atomic(ROOT/'verification.json',verification)
    registry={'campaign':'QUALITY-HOLDOUT-002','phase':'TERMINAL_'+summary['gates']['EXPERIMENT_COMPLETION'],'at':now(),
        'preparation':summary['preparation'],'gates':summary['gates'],'CPU_RECALCULATION_CHECK':'PASS',
        'next_exact_action':'Deliver verified per-family decision and stop. No retries, next experiment, tuning, deployment or push.'}
    atomic(ROOT/'registry.json',registry)
    handoff='# QUALITY-HOLDOUT-002 — consegna locale terminale\n\nPHASE: '+registry['phase']+'\nBASE_COMMIT: '+entry['base_commit']+'\nPREPARATION_COMMIT: '+summary['preparation']['preparation_commit']+'\nSOURCE_INDEX_SHA256: '+freeze['index_sha256']+'\n'
    handoff+='DELIVERY_COMMIT: resolve git log on this file after local delivery commit; no circular reference.\n\n'+json.dumps(summary['gates'],ensure_ascii=False,indent=2)+'\n\n'
    handoff+='RUN_A: '+m['runs']['A']['run_dir']+'\nRUN_B: '+m['runs']['B']['run_dir']+'\nROOT: '+str(ROOT)+'\n\n'
    handoff+='SOURCE_FREEZE preserved, original evidence unchanged, closed001/PERF untouched, scratch preserved. Native nonstreaming collectors; no replay/repair/grammar. K2 restore and own PID/unit/lock checks in restore-A.json/final-live.json. Surviving DS41 EngineCore processes are legitimate residents.\n\n'
    handoff+='CANONICAL: REPORT.md, summary.json, paired-results.jsonl, FINDINGS.md. Raw-results root is a derived index; evidence/ holds native copies and source hashes.\nCPU_RECALCULATION_CHECK: PASS; command/dependencies in verification.json.\n\nNEXT EXACT ACTION: deliver results and decision per family, then stop. No new inference, pilot, deployment, push or automatic experiment.\n'
    (ROOT/'HANDOFF.md').write_text(handoff)
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name!='DELIVERY-SHA256SUMS' and '__pycache__' not in p.parts)
    (ROOT/'DELIVERY-SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(ROOT))+'\n' for p in files))
    print(json.dumps({'status':'LOCAL_DELIVERY_VERIFIED','files_hashed':len(files),'verification':verification},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['snapshot','archive','verify']);p.add_argument('--arm',choices=['A','B']);p.add_argument('--filename');a=p.parse_args()
    if a.action=='snapshot':snapshot(a.arm,a.filename)
    elif a.action=='archive':archive()
    else:verify()
