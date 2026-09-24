"""Archive existing run evidence and verify restore; never starts/stops a model."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
from common import atomic,now,sha,verify_freeze
from window_guards import SSH,controller_status,unit_state,matching_compute_holders

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')


def read_peer(relative,profile,manifest):
    path=str(Path(manifest['runs'][profile]['run_dir'])/relative)
    code='import pathlib,sys; sys.stdout.buffer.write(pathlib.Path('+repr(path)+').read_bytes())'
    cp=subprocess.run(SSH+['/usr/bin/python3 -c '+shlex.quote(code)],capture_output=True,timeout=30)
    if cp.returncode:raise RuntimeError('PEER_READ_FAILED:'+relative+':'+cp.stderr.decode()[-500:])
    return cp.stdout


def archive(root,manifest):
    evidence=root/'evidence';evidence.mkdir(exist_ok=True);inventory=[]
    for profile,info in manifest['runs'].items():
        run=Path(info['run_dir'])
        if not run.exists():continue
        su=unit_state(info['supervisor_unit'])
        if su.get('ActiveState') not in ('inactive','failed') or int(su.get('MainPID','0'))!=0:raise RuntimeError('SUPERVISOR_NOT_TERMINAL:'+profile)
        result=json.loads((run/'result.json').read_text())
        if result.get('cleanup',{}).get('status')!='PASS':raise RuntimeError('RESTORE_NOT_COMPLETE:'+profile)
        for p in sorted(run.rglob('*')):
            if not p.is_file() or p.is_symlink() or p.name.endswith('.lock') or p.name=='compute-lock-held':continue
            relative=p.relative_to(run);dest=evidence/('run-'+profile)/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            h=sha(p)
            if dest.exists():
                if sha(dest)!=h:raise RuntimeError('ARCHIVED_BYTES_CHANGED:'+str(dest))
            else:shutil.copyfile(p,dest)
            if sha(p)!=h or sha(dest)!=h:raise RuntimeError('SOURCE_CHANGED_DURING_COPY')
            inventory.append({'source':str(p),'copy':str(dest),'sha256':h,'bytes':p.stat().st_size})
    if Path(manifest['runs']['O']['run_dir']).exists():
        data=read_peer('rank1-raw-results.jsonl','O',manifest);dest=evidence/'O-rank1-raw-results.jsonl'
        if dest.exists():
            if dest.read_bytes()!=data:raise RuntimeError('PEER_RAW_CHANGED')
        else:dest.write_bytes(data)
        remote_hash=subprocess.check_output(SSH+['sha256sum',str(Path(manifest['runs']['O']['run_dir'])/'rank1-raw-results.jsonl')],text=True,timeout=15).split()[0]
        if sha(dest)!=remote_hash:raise RuntimeError('PEER_TRANSFER_HASH')
        atomic(evidence/'peer-copy-receipt.json',{'node':'02-EVO-X3','path':str(Path(manifest['runs']['O']['run_dir'])/'rank1-raw-results.jsonl'),'sha256':remote_hash,'at':now()})
        for name in ['load-rank1.json','input-checks-rank1.json','arm-result-rank1.json','rank1.log']:
            data=read_peer(name,'O',manifest);p=evidence/('O-'+name)
            if p.exists():
                if p.read_bytes()!=data:raise RuntimeError('PEER_EVIDENCE_CHANGED:'+name)
            else:p.write_bytes(data)
    atomic(evidence/'archive-manifest.json',{'status':'PASS','at':now(),'files':inventory,'original_files_unchanged':len(inventory)})
    (evidence/'original-SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['source']+'\n' for x in inventory))
    return {'status':'PASS','files':len(inventory)}


def engines(peer=False):
    code="""import pathlib,json
out=[]
for p in pathlib.Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip();cg=(p/'cgroup').read_text().strip()
  if 'VLLM' in name or name.startswith(('ds4','llama')) or 'mimo26-gs001-' in cg:
   out.append({'pid':int(p.name),'name':name,'cgroup':cg})
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
print(json.dumps(out))
"""
    if peer:cp=subprocess.run(SSH+['/usr/bin/python3 -c '+shlex.quote(code)],capture_output=True,text=True,timeout=15)
    else:cp=subprocess.run(['/usr/bin/python3','-c',code],capture_output=True,text=True,timeout=10)
    if cp.returncode:raise RuntimeError('PROCESS_RECONCILIATION_FAILED')
    return json.loads(cp.stdout)


def final_live(root,manifest):
    st=controller_status();target=manifest['restore']
    if st.get('state')!='READY' or st.get('preset')!=target['preset'] or st.get('release_id')!=target['release_id']:raise RuntimeError('FINAL_RESIDENT_IDENTITY')
    if st.get('owner')!='DS41' or st.get('owner_state')!='RUNNING' or st.get('paired_backend_http')!='200' or not all(x.get('active') and x.get('health_http')=='200' for x in st.get('ranks',[])):raise RuntimeError('FINAL_RESIDENT_HEALTH')
    owner=json.loads(Path('/home/funboy/.local/state/strix-cluster/owner.json').read_text());units={};own={}
    for rank in ('0','1'):
        u=unit_state('ds41-rank'+rank+'.service',rank=='1');units[rank]=u
        if u.get('ActiveState')!='active' or u.get('InvocationID')!=owner.get('ranks',{}).get(rank,{}).get('invocation_id'):raise RuntimeError('FINAL_RESIDENT_INVOCATION')
    if owner.get('epoch')!=st.get('epoch'):raise RuntimeError('FINAL_OWNER_EPOCH')
    for profile,info in manifest['runs'].items():
        cfg=json.loads((root/info['config']).read_text())
        for key in ['rank0','rank1']:
            if cfg[key]:
                u=unit_state(cfg[key]['unit'],key=='rank1');own[profile+':'+key]=u
                if u.get('ActiveState') not in ('inactive','failed') or int(u.get('MainPID','0'))!=0:raise RuntimeError('OWN_WORKER_REMAINS')
    proc={'NODE01':engines(),'NODE02':engines(True)}
    if any('mimo26-gs001-' in e['cgroup'] for rows in proc.values() for e in rows):raise RuntimeError('OWN_PROCESS_REMAINS')
    holders=matching_compute_holders()
    if holders:raise RuntimeError('COMPUTE_LOCK_STILL_HELD')
    result={'status':'PASS','observed_at':now(),'controller':st,'owner':{k:owner.get(k) for k in ['owner','state','epoch','ranks']},'resident_units':units,'own_units':own,
        'engine_processes':proc,'lock_holders':holders,'note':'DS41 EngineCore cgroups are legitimate restored residents, not MiMo/Qwen residue. Read-only verification.'}
    atomic(root/'final-live.json',result)
    return result


def check_preserved(root):
    entry=json.loads((root/'preflight/entry.json').read_text());counts={}
    repo=root.parents[2]
    groups={'closed_campaigns':{path:value for inventory in entry['closed_campaigns'].values() for path,value in inventory.items()},'scratch':entry['scratch']}
    for key,inventory in groups.items():
        for relative,expected in inventory.items():
            if sha(repo/relative)!=expected:raise RuntimeError('PRESERVED_BYTES_CHANGED:'+relative)
        counts[key]=len(inventory)
    return counts


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['archive','live','check']);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();root=a.root.resolve()
    manifest=json.loads((root/'source-manifest.json').read_text());freeze=verify_freeze(root)
    if a.action=='archive':result=archive(root,manifest)
    elif a.action=='live':result=final_live(root,manifest)
    else:
        preserved=check_preserved(root)
        cp=subprocess.run(['/usr/bin/python3',str(root/'sources/evaluate.py'),'--root',str(root),'--check'],capture_output=True,text=True,timeout=120)
        (root/'verification-check.stdout').write_text(cp.stdout);(root/'verification-check.stderr').write_text(cp.stderr)
        if cp.returncode:raise RuntimeError('CPU_RECALCULATION_FAILED:'+cp.stderr[-1500:])
        inventory=json.loads((root/'evidence/archive-manifest.json').read_text())
        for x in inventory['files']:
            if sha(x['source'])!=x['sha256'] or sha(x['copy'])!=x['sha256']:raise RuntimeError('ARCHIVE_SOURCE_CHANGED')
        result={'status':'PASS','at':now(),'source_freeze':freeze,'CPU_RECALCULATION_CHECK':'PASS','original_files_unchanged':len(inventory['files']),'preserved':preserved}
        atomic(root/'verification.json',result)
    print(json.dumps(result if a.action!='live' else {'status':result['status'],'observed_at':result['observed_at'],'controller':result['controller']},indent=2))

if __name__=='__main__':main()
