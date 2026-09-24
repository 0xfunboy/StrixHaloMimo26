"""Exact pre-panel packaging recovery for E1's existing models endpoint."""
from pathlib import Path
import copy
import json
from common import sha,verify_freeze


def ready_models(body,model_id='deepseek-v4.1-flash',context=16384):
    if not isinstance(body,dict) or body.get('object')!='list':return False
    rows=body.get('data')
    return (isinstance(rows,list) and len(rows)==1 and isinstance(rows[0],dict)
            and rows[0].get('id')==model_id and rows[0].get('object')=='model'
            and rows[0].get('context_length')==context)


def verify_recovery(root):
    root=Path(root).resolve();base=verify_freeze(root)
    r=root/'recovery-D';index=r/'source-SHA256SUMS'
    for line in index.read_text().splitlines():
        h,rel=line.split('  ',1);p=(root/rel).resolve()
        if not p.is_relative_to(root) or sha(p)!=h:raise RuntimeError('D_RECOVERY_SOURCE_MISMATCH:'+rel)
    receipt=json.loads((r/'preparation.json').read_text())
    if receipt['base_index_sha256']!=base['index_sha256'] or receipt['recovery_index_sha256']!=sha(index):raise RuntimeError('D_RECOVERY_RECEIPT_MISMATCH')
    return {'status':'PASS','base':base,'recovery_index_sha256':sha(index),'preparation_commit':receipt['preparation_commit']}


def effective_manifest(root,original):
    manifest=copy.deepcopy(original)
    plan=json.loads((Path(root)/'recovery-D/manifest.json').read_text())
    manifest['runs']['D']=plan['run']
    cfg=manifest['profiles']['D'];cfg['peer_unit']=plan['peer_unit']
    cmd=list(cfg['command']);cmd[cmd.index('--trace')+1]=str(Path(plan['run']['run_dir'])/'server-trace.log');cfg['command']=cmd
    return manifest


def require_consumed_setup_restored(root):
    evidence=json.loads((Path(root)/'recovery-D/setup-evidence.json').read_text())
    run=Path('/home/funboy/.local/state/strixhalomimo26/windows')/evidence['run_id']
    if evidence['requests_sent']!=0 or (run/'requests').exists() or (run/'raw-results.jsonl').exists():raise RuntimeError('D_SETUP_ALREADY_SENT_REQUEST_NO_RETRY')
    result=json.loads((run/'result.json').read_text())
    if result.get('cleanup',{}).get('status')!='PASS':raise RuntimeError('D_SETUP_RESTORE_NOT_COMPLETE')
    from window_guards import unit_state
    unit=unit_state('mimo26-gs001-supervisor-d-001.service')
    if unit.get('ActiveState') not in ('inactive','failed') or int(unit.get('MainPID','0'))!=0:raise RuntimeError('D_SETUP_SUPERVISOR_ACTIVE')
    return result
