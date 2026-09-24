"""Idempotent selection dispatch/status/staging. Status never launches anything."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
from common import atomic,now,sha,verify_freeze
from window_guards import SSH,controller_status,unit_state

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')


def reconcile(root):
    manifest=json.loads((root/'source-manifest.json').read_text());result={'observed_at':now(),'controller':controller_status(),'profiles':{}}
    for profile,info in manifest['runs'].items():
        run=Path(info['run_dir']);r={'run_dir':str(run),'supervisor':unit_state(info['supervisor_unit'])}
        for name in ['dispatch.json','result.json','panel-progress.json','progress-rank0.json','fatal.json']:
            p=run/name
            if p.exists():
                obj=json.loads(p.read_text())
                if name=='result.json':obj={k:obj.get(k) for k in ['run_completion','initial_cause','cleanup','load']}
                if name=='result.json' and isinstance(obj.get('load'),dict):obj['load']={k:obj['load'].get(k) for k in ['status','load_s','pid']}
                r[name]=obj
        result['profiles'][profile]=r
    return result


def stage(root):
    manifest=json.loads((root/'source-manifest.json').read_text());freeze=verify_freeze(root);peer=manifest['peer_root']
    # Use a bounded archive of exact preregistered files. No models or secrets.
    files=[line.split('  ',1)[1] for line in (root/'source-SHA256SUMS').read_text().splitlines()]
    files+=['source-SHA256SUMS','preparation.json']
    identity=subprocess.check_output(SSH+['hostname'],text=True,timeout=10).strip()
    if identity!='02-EVO-X3':raise RuntimeError('PEER_IDENTITY_MISMATCH')
    check=subprocess.run(SSH+['test','-e',peer+'/source-SHA256SUMS'],capture_output=True,timeout=10)
    existing=check.returncode==0
    if not existing:
        subprocess.run(SSH+['mkdir','-p',peer],check=True,timeout=10)
        import tarfile
        with tempfile.TemporaryFile() as archive:
            with tarfile.open(fileobj=archive,mode='w') as tar:
                for name in files:
                    path=(root/name).resolve()
                    if not path.is_relative_to(root.resolve()):raise ValueError('unsafe staged path')
                    tar.add(path,arcname=name,recursive=False)
            archive.seek(0)
            unpack="""import pathlib,sys,tarfile
root=pathlib.Path(PEER_ROOT)
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|') as tar:
 for member in tar:
  if not member.isfile():raise ValueError('regular files only')
  p=(root/member.name).resolve()
  if not p.is_relative_to(root.resolve()):raise ValueError('unsafe archive path')
  data=tar.extractfile(member).read()
  p.parent.mkdir(parents=True,exist_ok=True)
  if p.exists():
   if p.read_bytes()!=data:raise ValueError('existing peer bytes differ: '+member.name)
  else:
   with p.open('xb') as f:f.write(data)
print('EXCLUSIVE_STAGE_COMPLETE')
""".replace('PEER_ROOT',repr(peer))
            command='/usr/bin/python3 -c '+shlex.quote(unpack)
            cp=subprocess.run(SSH+[command],stdin=archive,capture_output=True,text=True,timeout=90)
            if cp.returncode:raise RuntimeError('STAGE_UNCERTAIN_READ_PEER_BEFORE_RETRY:'+cp.stderr[-1000:])
    code="""import hashlib,json,pathlib,importlib.metadata
r=pathlib.Path(ROOT_VALUE)
entries=[]
for line in (r/'source-SHA256SUMS').read_text().splitlines():
 h,rel=line.split('  ',1);p=r/rel
 assert p.resolve().is_relative_to(r.resolve())
 assert hashlib.sha256(p.read_bytes()).hexdigest()==h,rel
 entries.append(rel)
m=json.loads((r/'source-manifest.json').read_text())
for p,h in m['profiles']['O']['binary_hashes'].items():
 assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
versions={k:importlib.metadata.version(k) for k in m['profiles']['O']['versions']}
assert versions==m['profiles']['O']['versions']
for k in ['binary','worker_binary']:
 b=m['profiles']['D'][k];assert hashlib.sha256(pathlib.Path(b['path']).read_bytes()).hexdigest()==b['sha256']
assert pathlib.Path(m['profiles']['D']['model_path']).stat().st_size==m['profiles']['D']['model_size']
print(json.dumps({'status':'PASS','files_checked':len(entries),'source_index_sha256':hashlib.sha256((r/'source-SHA256SUMS').read_bytes()).hexdigest(),'versions':versions}))
""".replace('ROOT_VALUE',repr(peer))
    cmd='/home/funboy/StrixHaloClusterGLM/.engine/venv/bin/python -c '+shlex.quote(code)
    cp=subprocess.run(SSH+[cmd],text=True,capture_output=True,timeout=45)
    if cp.returncode:raise RuntimeError('PEER_VERIFY_FAILED:'+cp.stderr[-1000:])
    result=json.loads(cp.stdout);result.update(node=identity,peer_root=peer,at=now(),existing_stage=existing)
    if result['source_index_sha256']!=freeze['index_sha256']:raise RuntimeError('PEER_INDEX_DISAGREEMENT')
    atomic(root/'preflight/peer-stage.json',result)
    return result


def dispatch(root,profile):
    root=root.resolve()
    from d_readiness_recovery_v1 import verify_recovery,effective_manifest,require_consumed_setup_restored
    verify_recovery(root);require_consumed_setup_restored(root)
    manifest=effective_manifest(root,json.loads((root/'source-manifest.json').read_text()));freeze=verify_freeze(root)
    if profile not in ('D','O'):raise RuntimeError('RECOVERY_LAUNCH_PROFILE_NOT_ALLOWED')
    prep=json.loads((root/'preparation.json').read_text())
    if prep['source_index_sha256']!=freeze['index_sha256']:raise RuntimeError('PREPARATION_INDEX_MISMATCH')
    if json.loads((root/'preflight/peer-stage.json').read_text())['source_index_sha256']!=freeze['index_sha256']:raise RuntimeError('PEER_NOT_STAGED')
    info=manifest['runs'][profile];run=Path(info['run_dir']);u=unit_state(info['supervisor_unit'])
    if run.exists() or u.get('LoadState')!='not-found':
        return {'state':'EXISTING_RUN_RECONCILE_NO_REDISPATCH','run':str(run),'supervisor':u}
    for earlier in manifest['order'][:manifest['order'].index(profile)]:
        previous=Path(manifest['runs'][earlier]['run_dir'])/'result.json'
        blocks=json.loads((root/'blockers.json').read_text()) if (root/'blockers.json').exists() else {}
        blocker=blocks.get(earlier,{})
        isolated=blocker.get('status')=='BLOCKED' and blocker.get('scope')=='ISOLATED_TO_PROFILE' and bool(blocker.get('reason')) and bool(blocker.get('evidence'))
        if not previous.exists():
            if manifest['profiles'][earlier]['status'].startswith('BLOCKED') and isolated:continue
            raise RuntimeError('PREVIOUS_PROFILE_NOT_TERMINAL:'+earlier)
        p=json.loads(previous.read_text())
        if (p.get('run_completion')!='PASS' and not isolated) or p.get('cleanup',{}).get('status')!='PASS':raise RuntimeError('PREVIOUS_PROFILE_REQUIRES_EXPLICIT_BLOCKER_TRIAGE:'+earlier)
        su=unit_state(manifest['runs'][earlier]['supervisor_unit'])
        if su.get('ActiveState') not in ('inactive','failed') or int(su.get('MainPID','0'))!=0:raise RuntimeError('PREVIOUS_RESTORE_STILL_ACTIVE')
    if json.loads((root/'preflight/acquire-weights.json').read_text())['status']!='PASS':raise RuntimeError('ACQUISITION_NOT_COMPLETE')
    st=controller_status()
    if st.get('state')!='READY':raise RuntimeError('RESIDENT_NOT_READY')
    run.mkdir(parents=True,exist_ok=False)
    config=json.loads((root/info['config']).read_text());atomic(run/'config.json',config,exclusive=True)
    (run/'frozen-SHA256SUMS').write_bytes((root/'source-SHA256SUMS').read_bytes())
    argv=['systemd-run','--user','--unit='+info['supervisor_unit'],'--property=Restart=no','--property=KillMode=control-group',
          '--property=RuntimeMaxSec='+str(info['supervisor_runtime_s']),'--property=TimeoutStopSec='+str(info['supervisor_stop_s']),
          '--property=ExecStopPost=/usr/bin/python3 '+str(root/'sources/window_cleanup.py')+' '+info['run_id'],
          '--property=StandardOutput=append:'+str(run/'supervisor.log'),'--property=StandardError=append:'+str(run/'supervisor.log'),
          '--','/usr/bin/python3',str(root/('sources/window_runner_d_readiness_v1.py' if profile=='D' else 'sources/window_runner.py')),info['run_id']]
    atomic(run/'dispatch.json',{'state':'INTENT','at':now(),'profile':profile,'source_index_sha256':freeze['index_sha256'],'preparation_commit':prep['preparation_commit'],'command':argv},exclusive=True)
    try:
        cp=subprocess.run(argv,capture_output=True,text=True,timeout=20)
        result={'state':'DISPATCHED' if cp.returncode==0 else 'DISPATCH_FAILED','at':now(),'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr,'supervisor':unit_state(info['supervisor_unit'])}
    except subprocess.TimeoutExpired:
        result={'state':'CALL_TIMEOUT_RECONCILE_NO_REDISPATCH','at':now(),'supervisor':unit_state(info['supervisor_unit'])}
    atomic(run/'dispatch-result.json',result,exclusive=True)
    atomic(root/'registry.json',{'campaign':manifest['campaign'],'phase':'WINDOW_'+profile,'at':now(),'run_id':info['run_id'],'dispatch_state':result['state'],
        'next_exact_action':'Read the existing supervisor/run receipts until collection and restore are terminal; never redispatch an uncertain request.'})
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['status','stage-peer','launch']);p.add_argument('profile',nargs='?',choices=['Q','M','D','O']);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args()
    if a.action=='status':result=reconcile(a.root)
    elif a.action=='stage-peer':result=stage(a.root)
    else:
        if a.profile is None:p.error('profile required for launch')
        result=dispatch(a.root,a.profile)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
