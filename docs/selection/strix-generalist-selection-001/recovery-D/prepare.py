"""Create new packaging-only D sources without changing original frozen files."""
from pathlib import Path
import ast
import copy
import difflib
import json

R=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
S=R/'sources';HERE=R/'recovery-D'

def write_new(p,data):
    if p.exists():
        if p.read_text()!=data:raise RuntimeError('EXISTING_RECOVERY_BYTES_DIFFER:'+str(p))
    else:p.write_text(data)

def transform(source,dest,edits):
    before=(S/source).read_text();after=before
    for old,new in edits:
        if after.count(old)!=1:raise RuntimeError('EXACT_PATCH_NOT_UNIQUE:'+source)
        after=after.replace(old,new,1)
    ast.parse(after);write_new(S/dest,after)
    write_new(HERE/(dest+'.diff'),''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=source,tofile=dest)))

def main():
    if (HERE/'source-SHA256SUMS').exists():raise RuntimeError('D_RECOVERY_ALREADY_FROZEN')
    old=json.loads((R/'source-manifest.json').read_text());prior=old['runs']['D'];new=copy.deepcopy(prior)
    new.update(run_id='generalist-selection-001-D-002',run_dir=str(Path(prior['run_dir']).parent/'generalist-selection-001-D-002'),
               config='recovery-D/config-D.json',supervisor_unit='mimo26-gs001-supervisor-d-002.service')
    cfg=copy.deepcopy(json.loads((R/'config-D.json').read_text()));cfg['run_id']=new['run_id']
    for name in ('rank0','rank1'):
        cfg[name]['unit']=cfg[name]['unit'].removesuffix('001')+'002'
        cfg[name]['argv']=[v.replace('GS_RUN_DIR='+prior['run_dir'],'GS_RUN_DIR='+new['run_dir']) for v in cfg[name]['argv']]
    cfg['rank0']['argv'][-1]=str(S/'adapter_ds41_readiness_v1.py')
    plan={'status':'PREREGISTERED_PACKAGING_RECOVERY','prior_run':prior,'run':new,'peer_unit':cfg['rank1']['unit'],
          'max_packaging_recoveries':1,'reason':'Existing /v1/models readiness instead of nonexistent /health; zero prior generated requests.',
          'preserved':'All cases, expected, tokenizer/input IDs, sampling, budgets, binaries and numerical runtime unchanged.'}
    write_new(HERE/'manifest.json',json.dumps(plan,indent=2)+'\n');write_new(HERE/'config-D.json',json.dumps(cfg,indent=2)+'\n')
    transform('adapter_ds41.py','adapter_ds41_readiness_v1.py',[
        ("    frozen=verify_freeze(root);manifest=json.loads((root/'source-manifest.json').read_text());cfg=manifest['profiles']['D']",
         "    from d_readiness_recovery_v1 import ready_models,verify_recovery,effective_manifest\n    recovery=verify_recovery(root)\n    frozen=verify_freeze(root);manifest=effective_manifest(root,json.loads((root/'source-manifest.json').read_text()));cfg=manifest['profiles']['D']\n    atomic(run/'recovery-source-receipt.json',recovery,exclusive=True)"),
        ("                health=http(base,'/health',timeout=2)\n                if health.get('status')=='ok':break",
         "                health=http(base,'/v1/models',timeout=2)\n                if ready_models(health,cfg['api_model'],16384):break")])
    transform('window_guards.py','window_guards_d_readiness_v1.py',[
        ("    if sha(run/'config.json')!=sha(root/manifest['runs'][cfg['profile']]['config']):raise RuntimeError('CONFIG_FREEZE_MISMATCH')",
         "    from d_readiness_recovery_v1 import verify_recovery,effective_manifest,require_consumed_setup_restored\n    verify_recovery(root);require_consumed_setup_restored(root)\n    manifest=effective_manifest(root,manifest)\n    if cfg['profile']!='D' or run.name!=manifest['runs']['D']['run_id']:raise RuntimeError('WRONG_D_RECOVERY_RUN')\n    if sha(run/'config.json')!=sha(root/manifest['runs']['D']['config']):raise RuntimeError('CONFIG_RECOVERY_MISMATCH')")])
    transform('window_runner.py','window_runner_d_readiness_v1.py',[
        ('from window_guards import preflight','from window_guards_d_readiness_v1 import preflight')])
    transform('launch.py','launch_d_readiness_v1.py',[
        ("    root=root.resolve();manifest=json.loads((root/'source-manifest.json').read_text());freeze=verify_freeze(root)",
         "    root=root.resolve()\n    from d_readiness_recovery_v1 import verify_recovery,effective_manifest,require_consumed_setup_restored\n    verify_recovery(root);require_consumed_setup_restored(root)\n    manifest=effective_manifest(root,json.loads((root/'source-manifest.json').read_text()));freeze=verify_freeze(root)\n    if profile not in ('D','O'):raise RuntimeError('RECOVERY_LAUNCH_PROFILE_NOT_ALLOWED')"),
        ("return {'state':'EXISTING_RUN_RECONCILE_NO_REDISPATCH','run':str(run),'supervisor':u,'snapshot':reconcile(root)['profiles'][profile]}",
         "return {'state':'EXISTING_RUN_RECONCILE_NO_REDISPATCH','run':str(run),'supervisor':u}"),
        ("str(root/'sources/window_runner.py'),info['run_id']", "str(root/('sources/window_runner_d_readiness_v1.py' if profile=='D' else 'sources/window_runner.py')),info['run_id']")])
    print(json.dumps({'status':'D_PACKAGING_RECOVERY_PREPARED','new_run':new['run_id'],'original_files_changed':0,'panel_requests_repeated':0}))

if __name__=='__main__':main()
