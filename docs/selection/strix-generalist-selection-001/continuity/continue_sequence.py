"""Continue only the already authorized serial windows; no retries or new experiment."""
from pathlib import Path
import datetime
import fcntl
import json
import subprocess
import sys
import time

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
sys.path.insert(0,str(ROOT/'sources'))
from common import atomic
from mtp_process_v1 import verify_addendum
from window_guards import controller_status,unit_state


def stamp():return datetime.datetime.now().astimezone().isoformat()
def read(path):return json.loads(path.read_text()) if path.exists() else {}


def main():
    if subprocess.check_output(['hostname'],text=True).strip()!='01-EVO-X3':raise RuntimeError('WRONG_HOST')
    lock=(ROOT/'continuity/sequence.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    verify_addendum(ROOT)
    manifest=read(ROOT/'source-manifest.json');add=read(ROOT/'continuity/addendum.json')
    runs=dict(manifest['runs']);runs['T']=add['mtp_run']
    deadline=time.monotonic()+285200
    phases=[]
    def persist(state,**fields):
        data={'status':state,'observed_at':stamp(),'phases':phases,'script':str(Path(__file__).resolve()),**fields}
        atomic(ROOT/'continuity/sequence.json',data)
        print(json.dumps(data),flush=True)
    persist('RECONCILING_EXISTING_Q')
    if not Path(runs['Q']['run_dir']).exists():raise RuntimeError('EXPECTED_EXISTING_Q_MISSING_NO_DISPATCH')
    for profile in ['Q','M','D','O','T']:
        info=runs[profile];run=Path(info['run_dir'])
        if profile=='T' and not run.exists():
            q=read(Path(runs['Q']['run_dir'])/'result.json')
            off=read(Path(runs['Q']['run_dir'])/'mtp-off/summary.json')
            if q.get('run_completion')!='PASS' or q.get('cleanup',{}).get('status')!='PASS' or off.get('status')!='COMPLETE' or off.get('records')!=12:
                phases.append({'profile':'T','status':'NOT_ADMITTED','reason':'Q execution/restore or OFF reference gate not satisfied','at':stamp()})
                continue
        if not run.exists():
            persist('DISPATCH_INTENT',profile=profile,run_id=info['run_id'])
            try:
                cp=subprocess.run(['/usr/bin/python3',str(ROOT/'sources/launch_continuity_v1.py'),'launch',profile],capture_output=True,text=True,timeout=60)
            except subprocess.TimeoutExpired:
                persist('BLOCKED_DISPATCH_TIMEOUT_RECONCILE_ONLY',profile=profile,run_id=info['run_id']);return 2
            if cp.returncode:
                persist('BLOCKED_LAUNCH',profile=profile,run_id=info['run_id'],returncode=cp.returncode,stderr=cp.stderr[-2000:],stdout=cp.stdout[-2000:]);return 3
            atomic(ROOT/'continuity'/('sequence-launch-'+profile+'.json'),{'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr,'at':stamp()},exclusive=True)
        previous=None
        while time.monotonic()<deadline:
            unit=unit_state(info['supervisor_unit']);result=read(run/'result.json');progress=read(run/'panel-progress.json')
            current={'profile':profile,'run_id':info['run_id'],'unit':unit,'run_completion':result.get('run_completion'),'cleanup':result.get('cleanup'),'progress':progress}
            serial=json.dumps(current,sort_keys=True)
            if serial!=previous:persist('WINDOW_RECONCILIATION',**current);previous=serial
            if unit.get('ActiveState') in ('inactive','failed') and int(unit.get('MainPID','0'))==0:
                if result.get('cleanup',{}).get('status')!='PASS':
                    persist('BLOCKED_RESTORE',**current);return 4
                resident=controller_status()
                if resident.get('state')!='READY' or resident.get('release_id')!=manifest['restore']['release_id']:
                    persist('BLOCKED_RESIDENT_STATE',**current,resident=resident);return 5
                if result.get('run_completion')!='PASS':
                    blocker=read(ROOT/'blockers.json').get(profile,{})
                    if blocker.get('status')!='BLOCKED' or blocker.get('scope')!='ISOLATED_TO_PROFILE':
                        persist('BLOCKED_PROFILE_REQUIRES_CAUSAL_CLASSIFICATION',**current,fatal=read(run/'fatal.json'));return 6
                phases.append({'profile':profile,'run_id':info['run_id'],'status':result.get('run_completion'),'restore':result.get('cleanup'),'at':stamp()})
                break
            time.sleep(5)
        else:persist('BLOCKED_SEQUENCE_DEADLINE',profile=profile);return 7
    persist('AUTHORIZED_WINDOWS_TERMINAL',resident=controller_status(),next_exact_action='CPU-only archive, effective continuity evaluation/check, final local delivery; no further model request.')
    return 0

if __name__=='__main__':raise SystemExit(main())
