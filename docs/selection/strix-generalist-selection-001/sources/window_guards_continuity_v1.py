"""Read-only admission checks for the existing resident before controlled windows."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import urllib.request
from common import atomic,now,sha,verify_freeze

SSH=['ssh','-o','IdentityAgent=none','-o','BatchMode=yes','-o','ConnectTimeout=5','02-evo-x3-tb']
OWNER=Path('/home/funboy/.local/state/strix-cluster/owner.json')
REL=Path('/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6')
CONTROLLER=REL/'runtime/ds41/serve-controller.sh'


def command(argv,timeout=15):
    cp=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
    if cp.returncode:raise RuntimeError('READ_FAILED:'+str(argv[0])+':'+cp.stderr[-800:])
    return cp.stdout


def unit_state(unit,peer=False):
    cmd=['systemctl','--user','show',unit,'-p','LoadState','-p','ActiveState','-p','SubState','-p','MainPID','-p','InvocationID','-p','Result','-p','ExecMainStatus']
    text=command((SSH+cmd) if peer else cmd)
    return dict(line.split('=',1) for line in text.splitlines() if '=' in line)


def controller_status():
    cp=subprocess.run([str(CONTROLLER),'status'],env={**os.environ,'DS41_ROOT':str(REL)},capture_output=True,text=True,timeout=30)
    try:return json.loads(cp.stdout)
    except ValueError:raise RuntimeError('CONTROLLER_UNREADABLE:'+cp.stderr[-500:])


def matching_compute_holders():
    raw=command(['lslocks','--noheadings','-o','PID,COMMAND,PATH'])
    return [x for x in raw.splitlines() if '/strix-cluster/compute.lock' in x or '/strixhalomimo26/cleanup-global.lock' in x]


def validate_resident(st,owner,units,health):
    if st.get('state')!='READY':raise RuntimeError('RESIDENT_NOT_READY:'+str(st.get('state')))
    if st.get('preset')!='dspark-k2-gfx1151' or st.get('release_id')!='5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513':raise RuntimeError('RESTORE_IDENTITY_CHANGED')
    if owner.get('owner')!='DS41' or owner.get('state')!='RUNNING' or st.get('epoch')!=owner.get('epoch'):raise RuntimeError('RESIDENT_OWNER_CHANGED')
    ranks=st.get('ranks',[])
    if len(ranks)!=2 or not all(x.get('active') is True and x.get('health_http')=='200' for x in ranks) or st.get('paired_backend_http')!='200':raise RuntimeError('RESIDENT_HEALTH_INCOMPLETE')
    for rank in ('0','1'):
        u=units[rank];receipt=owner.get('ranks',{}).get(rank,{})
        if u.get('ActiveState')!='active' or int(u.get('MainPID','0'))<=0 or u.get('InvocationID')!=receipt.get('invocation_id'):raise RuntimeError('RESIDENT_INVOCATION_MISMATCH:'+rank)
    if health.get('status')!='ok' or health.get('busy') is not False or health.get('poison'):raise RuntimeError('RESIDENT_BUSY_OR_POISONED')
    return True


def preflight(root,run,cfg):
    root=Path(root).resolve();run=Path(run)
    assert cfg['campaign']=='STRIX-GENERALIST-SELECTION-001'
    manifest=json.loads((root/'source-manifest.json').read_text())
    freeze=verify_freeze(root)
    from mtp_process_v1 import verify_addendum
    verify_addendum(root)
    add=json.loads((root/'continuity/addendum.json').read_text())
    config_path=add['config_by_run'].get(run.name)
    if config_path is None or sha(run/'config.json')!=sha(root/config_path):raise RuntimeError('CONFIG_ADDENDUM_MISMATCH')
    if command(['hostname']).strip()!='01-EVO-X3' or command(['id','-un']).strip()!='funboy':raise RuntimeError('NODE01_IDENTITY')
    peer=command(SSH+['sh','-c',"'hostname; id -un; cat /proc/sys/kernel/random/boot_id'"])
    if peer.splitlines()[:2]!=['02-EVO-X3','funboy']:raise RuntimeError('NODE02_IDENTITY')
    owner=json.loads(OWNER.read_text());units={'0':unit_state('ds41-rank0.service'),'1':unit_state('ds41-rank1.service',True)}
    st=controller_status()
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:18221/health',timeout=5) as resp:health=json.loads(resp.read())
    validate_resident(st,owner,units,health)
    holders=matching_compute_holders()
    if holders:raise RuntimeError('COMPUTE_OR_CLEANUP_LOCK_BUSY')
    for name in ['acquire-weights','qwen-build-002']:
        p=root/'preflight'/(name+'.json')
        if p.exists() and json.loads(p.read_text()).get('status')=='IN_FLIGHT':raise RuntimeError('BACKGROUND_PREPARATION_NOT_TERMINAL:'+name)
    for rank in ('rank0','rank1'):
        if cfg.get(rank):
            state=unit_state(cfg[rank]['unit'],rank=='rank1')
            if state.get('LoadState')!='not-found' or int(state.get('MainPID','0'))!=0:raise RuntimeError('WORKER_UNIT_ALREADY_EXISTS:'+rank)
    ports=command(['ss','-H','-ltn'])
    for port in cfg.get('reserved_ports',[]):
        if any(line.split()[3].endswith(':'+str(port)) for line in ports.splitlines() if len(line.split())>=4):raise RuntimeError('PORT_IN_USE:'+str(port))
    for source,expected in manifest['resident_lifecycle_hashes'].items():
        if sha(source)!=expected:raise RuntimeError('RESIDENT_SOURCE_CHANGED:'+source)
    record={'status':'PASS','at':now(),'controller':st,'owner':{k:owner.get(k) for k in ['owner','state','epoch','updated','ranks']},'resident_units':units,
            'paired_health':health,'freeze':freeze,'peer_identity':peer.splitlines(),'matching_compute_holders':holders,
            'restore_target':{'controller':str(CONTROLLER),'release':str(REL),'preset':st['preset'],'release_id':st['release_id']},'own_profile':cfg['profile']}
    atomic(run/'admission.json',record,exclusive=True)
    return record
