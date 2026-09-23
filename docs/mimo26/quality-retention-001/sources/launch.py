"""Guarded dispatcher for the unchanged qualified window supervisor; no retries."""
from __future__ import annotations
import argparse
import io
import json
import os
import shlex
import subprocess
import tarfile
from pathlib import Path
from common import atomic,now,sha,verify_freeze

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/mimo26/quality-retention-001')
SSH=['ssh','-o','IdentityAgent=none','-o','BatchMode=yes','-o','ConnectTimeout=5','02-evo-x3-tb']
REPO=Path('/home/funboy/StrixHaloMimo26')


def command(args,timeout=20):
    return subprocess.run([str(x) for x in args],text=True,capture_output=True,timeout=timeout,check=True)


def unit_status(unit,peer=False):
    args=['systemctl','--user','show',unit,'-p','LoadState','-p','ActiveState','-p','SubState','-p','MainPID','-p','InvocationID','-p','Result','-p','ExecMainStatus']
    cp=subprocess.run(SSH+[shlex.join(args)] if peer else args,text=True,capture_output=True,timeout=20)
    parsed=dict(line.split('=',1) for line in cp.stdout.splitlines() if '=' in line)
    if 'LoadState' not in parsed or (cp.returncode and parsed.get('LoadState')!='not-found'):
        raise RuntimeError('UNIT_STATE_UNKNOWN:'+unit+':'+cp.stderr[:400])
    return parsed


def controller(manifest):
    cp=command([manifest['restore']['controller'],'status'])
    return json.loads(cp.stdout)


def stage_peer(manifest):
    verify_freeze(ROOT)
    peer_root=manifest['peer_root']
    identity=command(SSH+['hostname; id -un']).stdout.splitlines()
    assert identity==['02-EVO-X3','funboy'],'PEER_IDENTITY_MISMATCH'
    present=command(SSH+[f'test -d {shlex.quote(peer_root)} && echo EXISTS || echo ABSENT']).stdout.strip()
    if present=='ABSENT':
        entries=[]
        for line in (ROOT/'source-SHA256SUMS').read_text().splitlines():entries.append(line.split('  ',1)[1])
        entries.append('source-SHA256SUMS')
        data=io.BytesIO()
        with tarfile.open(fileobj=data,mode='w') as tar:
            for rel in entries:
                p=ROOT/rel
                assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT.resolve())
                tar.add(p,arcname=rel,recursive=False)
        remote=f'mkdir -p {shlex.quote(str(Path(peer_root).parent))} && mkdir {shlex.quote(peer_root)} && tar --no-same-owner -xf - -C {shlex.quote(peer_root)}'
        cp=subprocess.run(SSH+[remote],input=data.getvalue(),capture_output=True,timeout=45)
        if cp.returncode:raise RuntimeError('PEER_STAGE_FAILED_RECONCILE_EXISTING_DIR:'+cp.stderr.decode()[:1200])
    # Existing complete stage is a no-op; incomplete/different stage is a blocker, never overwritten.
    check=command(SSH+[f'cd {shlex.quote(peer_root)} && sha256sum -c source-SHA256SUMS'],timeout=30)
    code='import importlib.metadata as m,json; print(json.dumps({k:m.version(k) for k in '+repr(list(manifest['runtimes']['B']['versions']))+'}))'
    versions=json.loads(command(SSH+[shlex.join(['/home/funboy/StrixHaloClusterGLM/.engine/venv/bin/python','-c',code])]).stdout)
    assert versions==manifest['runtimes']['B']['versions'],'PEER_VERSION_PIN_MISMATCH'
    code='import hashlib,json; from pathlib import Path; paths='+repr(list(manifest['runtimes']['B']['binary_hashes']))+'; print(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}))'
    binary_hashes=json.loads(command(SSH+[shlex.join(['/usr/bin/python3','-c',code])],timeout=60).stdout)
    assert binary_hashes==manifest['runtimes']['B']['binary_hashes'],'PEER_VLLM_BINARY_MISMATCH'
    remote_index=command(SSH+['sha256sum '+shlex.quote(peer_root+'/source-SHA256SUMS')]).stdout.split()[0]
    assert remote_index==sha(ROOT/'source-SHA256SUMS')
    rec={'status':'PASS','at':now(),'node':'02-EVO-X3','peer_root':peer_root,'source_index_sha256':remote_index,
         'verified_files':len(check.stdout.splitlines()),'runtime_versions':versions,'binary_hashes':binary_hashes,'existing_stage':present=='EXISTS'}
    atomic(ROOT/'preflight/peer-stage.json',rec)
    print(json.dumps(rec))


def inspect(manifest,arm=None):
    arms=[arm] if arm else ['A','B'];out={'observed_at':now(),'controller':controller(manifest),'arms':{}}
    for a in arms:
        spec=manifest['runs'][a];run=Path(spec['run_dir'])
        row={'run_dir':str(run),'supervisor':unit_status(spec['supervisor_unit'])}
        for name in ('result.json','panel-progress.json','progress-rank0.json','fatal.json','fatal-rank0.json','k2-after.json'):
            if (run/name).exists():
                d=json.loads((run/name).read_text())
                if name=='result.json':d={k:d.get(k) for k in ('run_completion','initial_cause','cleanup')}
                row[name]=d
        if (run/'raw-results.jsonl').exists():row['primary_raw_count']=len((run/'raw-results.jsonl').read_text().splitlines())
        out['arms'][a]=row
    print(json.dumps(out,indent=2))


def launch(manifest,arm):
    freeze=verify_freeze(ROOT)
    prep=json.loads((ROOT/'preparation.json').read_text())
    assert prep['source_index_sha256']==freeze['index_sha256']
    command(['git','-C',REPO,'merge-base','--is-ancestor',prep['preparation_commit'],'HEAD'])
    binary=manifest['runtimes']['A']['binary']
    assert sha(binary['path'])==binary['sha256'],'A_BINARY_PIN_CHANGED'
    code='import importlib.metadata as m,json; print(json.dumps({k:m.version(k) for k in '+repr(list(manifest['runtimes']['B']['versions']))+'}))'
    versions=json.loads(command(['/home/funboy/StrixHaloClusterGLM/.engine/venv/bin/python','-c',code]).stdout)
    assert versions==manifest['runtimes']['B']['versions'],'NODE01_RUNTIME_PIN_CHANGED'
    for path,expected in manifest['runtimes']['B']['binary_hashes'].items():assert sha(path)==expected,'NODE01_B_BINARY_PIN_CHANGED'
    for path,expected in manifest['external_lifecycle_hashes'].items():assert sha(path)==expected,'RESIDENT_LIFECYCLE_CHANGED'
    for path,expected in manifest['tokenizer_files'].items():assert sha(path)==expected,'TOKENIZER_PIN_CHANGED'
    for path,expected in manifest['runtimes']['A']['shared_library_hashes'].items():assert sha(path)==expected,'A_LIBRARY_PIN_CHANGED'
    peer_stage=json.loads((ROOT/'preflight/peer-stage.json').read_text())
    assert peer_stage['status']=='PASS' and peer_stage['source_index_sha256']==freeze['index_sha256']
    stage_check=command(SSH+[f'cd {shlex.quote(manifest["peer_root"])} && sha256sum -c source-SHA256SUMS'],timeout=30)
    assert stage_check.returncode==0
    assert command(['hostname']).stdout.strip()=='01-EVO-X3'
    assert command(['id','-un']).stdout.strip()=='funboy'
    assert command(SSH+['hostname; id -un']).stdout.splitlines()==['02-EVO-X3','funboy']
    for a in ('A','B'):
        st=unit_status(manifest['runs'][a]['supervisor_unit'])
        assert st['ActiveState'] not in ('active','activating','deactivating'),'EXISTING_SUPERVISOR_MUST_BE_RECONCILED'
    spec=manifest['runs'][arm];run=Path(spec['run_dir'])
    assert not run.exists(),'RUN_DIRECTORY_EXISTS_RECONCILE_DO_NOT_REDISPATCH'
    cfg=json.loads((ROOT/spec['config']).read_text())
    for rank in (0,1):
        w=cfg.get('rank'+str(rank))
        if w:assert unit_status(w['unit'],peer=rank==1)['ActiveState'] not in ('active','activating','deactivating'),'WORKER_ALREADY_ACTIVE'
    status=controller(manifest)
    assert status['state']=='READY' and status['owner']=='DS41' and status['owner_state']=='RUNNING','OWNER_OR_STATE_NOT_SAFE'
    assert status['preset']==manifest['restore']['preset'] and status['release_id']==manifest['restore']['release_id'],'RESTORE_TARGET_DIVERGENCE'
    health=json.loads(command(['curl','--noproxy','*','-fsS','--max-time','5','http://127.0.0.1:18221/health']).stdout)
    assert health.get('busy') is False and not health.get('poison'),'RESIDENT_NOT_IDLE'
    owner=json.loads(Path('/home/funboy/.local/state/strix-cluster/owner.json').read_text())
    for rank in (0,1):
        active=unit_status('ds41-rank'+str(rank)+'.service',peer=rank==1)
        assert active['ActiveState']=='active' and active['InvocationID']==owner['ranks'][str(rank)]['invocation_id'],'OWNER_INVOCATION_MISMATCH'
    locks=command(['lslocks','--noheadings','-o','PID,COMMAND,PATH']).stdout
    assert '/strix-cluster/compute.lock' not in locks and '/strixhalomimo26/cleanup-global.lock' not in locks,'RESOURCE_LOCK_BUSY'
    sockets=command(['ss','-lnt']).stdout
    assert ':18342 ' not in sockets and ':29641 ' not in sockets,'REQUEST_OR_RENDEZVOUS_PORT_BUSY'
    if arm=='B':
        a_run=Path(manifest['runs']['A']['run_dir']);a=json.loads((a_run/'result.json').read_text())
        assert a['run_completion']=='PASS' and a['cleanup']['status']=='PASS','A_NOT_TERMINAL_RESTORED_PASS'
        aquality=json.loads((a_run/'quality.json').read_text());assert aquality['status']=='PASS' and aquality['panel_completions']==24
        ast=json.loads((a_run/'k2-after.json').read_text());assert ast['state']=='READY' and ast['release_id']==status['release_id']
    run.mkdir(parents=True)
    (run/'config.json').write_bytes((ROOT/spec['config']).read_bytes())
    (run/'frozen-SHA256SUMS').write_bytes((ROOT/'source-SHA256SUMS').read_bytes())
    atomic(run/'dispatch-preflight.json',{'observed_at':now(),'controller':status,'paired_health':health,'freeze':freeze,
        'preparation_commit':prep['preparation_commit'],'owner_invocations':{k:v['invocation_id'] for k,v in owner['ranks'].items()}})
    args=['systemd-run','--user','--unit='+spec['supervisor_unit'],'--property=Type=simple',
        '--property=KillMode=control-group','--property=Restart=no','--property=TimeoutStartSec=120',
        '--property=TimeoutStopSec='+str(spec['supervisor_stop_s']),'--property=RuntimeMaxSec='+str(spec['supervisor_runtime_s']),
        '--property=Environment=PYTHONDONTWRITEBYTECODE=1',
        '--property=ExecStopPost=/usr/bin/python3 '+str(ROOT/'sources/window_cleanup.py')+' '+spec['run_id'],
        '--property=StandardOutput=append:'+str(run/'supervisor.log'),'--property=StandardError=append:'+str(run/'supervisor.log'),
        '--','/usr/bin/python3',str(ROOT/'sources/window_runner.py'),spec['run_id']]
    atomic(run/'dispatch.json',{'state':'DISPATCHING_DO_NOT_RETRY','at':now(),'command':args},exclusive=True)
    cp=command(args,timeout=20)
    rec={'state':'DISPATCHED','at':now(),'stdout':cp.stdout,'stderr':cp.stderr,'supervisor':unit_status(spec['supervisor_unit'])}
    atomic(run/'dispatch-result.json',rec,exclusive=True)
    atomic(ROOT/'registry.json',{'campaign':'QUALITY-RETENTION-001','phase':arm+'_IN_FLIGHT','run_id':spec['run_id'],
        'unit':spec['supervisor_unit'],'invocation_id':rec['supervisor']['InvocationID'],'at':now(),
        'next_exact_action':'Read existing supervisor, result/progress and cleanup; never dispatch this run again.'})
    (ROOT/'HANDOFF.md').write_text('# QUALITY-RETENTION-001\n\nPHASE: '+arm+'_IN_FLIGHT\nPREPARATION_COMMIT: '+prep['preparation_commit']+'\nRUN: '+str(run)+'\nUNIT: '+spec['supervisor_unit']+'\nINVOCATION_ID: '+rec['supervisor']['InvocationID']+'\nSOURCE_INDEX_SHA256: '+freeze['index_sha256']+'\nNEXT EXACT ACTION: inspect existing run progress and restore. Do not redispatch after an MCP timeout. The qualified finalizer runs through ExecStopPost.\n')
    print(json.dumps(rec,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['stage-peer','status','launch']);p.add_argument('--arm',choices=['A','B']);a=p.parse_args()
    manifest=json.loads((ROOT/'source-manifest.json').read_text())
    if a.action=='stage-peer':stage_peer(manifest)
    elif a.action=='status':inspect(manifest,a.arm)
    else:
        if not a.arm:p.error('--arm required')
        launch(manifest,a.arm)
