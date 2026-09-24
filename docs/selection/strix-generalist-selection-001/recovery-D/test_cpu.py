"""CPU-only readiness tests using the saved REAL E1 responses, not invented schema."""
from pathlib import Path
import copy
import json
import sys
import ast
R=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001');sys.path.insert(0,str(R/'sources'))
from d_readiness_recovery_v1 import ready_models,effective_manifest
from common import sha

def main():
    ev=json.loads((R/'recovery-D/setup-evidence.json').read_text());body=ev['endpoints']['/v1/models']['body']
    checks=[]
    def check(name,predicate):
        if not predicate:raise AssertionError(name)
        checks.append(name)
    check('real captured models admits exact identity',ready_models(body))
    check('real captured 404 rejected',not ready_models(ev['endpoints']['/health']['body']))
    for name,mutator in [('wrong identity',lambda x:x['data'][0].update(id='wrong')),('wrong context',lambda x:x['data'][0].update(context_length=4096)),
                         ('multiple models',lambda x:x['data'].append(dict(x['data'][0]))),('empty list',lambda x:x.update(data=[])),
                         ('wrong top-level object',lambda x:x.update(object='model'))]:
        bad=copy.deepcopy(body);mutator(bad);check(name,not ready_models(bad))
    for v in [None,[],{'data':None},{'object':'list','data':[None]},{'object':'list','data':{}}]:check('invalid shape '+repr(v),not ready_models(v))
    original=json.loads((R/'source-manifest.json').read_text());oldcopy=copy.deepcopy(original);new=effective_manifest(R,original)
    check('original manifest immutable',original==oldcopy)
    for key in ['Q','M','O']:check(key+' config unchanged',new['profiles'][key]==original['profiles'][key] and new['runs'][key]==original['runs'][key])
    d=copy.deepcopy(new['profiles']['D']);d['peer_unit']=original['profiles']['D']['peer_unit'];d['command'][d['command'].index('--trace')+1]=original['profiles']['D']['command'][-1]
    check('D only trace/unit identity changed',d==original['profiles']['D'])
    adapter=(R/'sources/adapter_ds41_readiness_v1.py').read_text();old=(R/'sources/adapter_ds41.py').read_text()
    check('collection and scoring body unchanged',adapter.split('        checks={};sequence=0',1)[1]==old.split('        checks={};sequence=0',1)[1])
    check('request bytes unchanged',sha(R/'requests-D.jsonl')==next(line.split('  ',1)[0] for line in (R/'source-SHA256SUMS').read_text().splitlines() if line.endswith('  requests-D.jsonl')))
    check('D new run identity',new['runs']['D']['run_id']=='generalist-selection-001-D-002')
    for p in list((R/'sources').glob('*readiness*v1.py'))+[R/'sources/d_readiness_recovery_v1.py']:ast.parse(p.read_text())
    for line in (R/'source-SHA256SUMS').read_text().splitlines():
        h,name=line.split('  ',1);check('base '+name,sha(R/name)==h)
    result={'status':'PASS','checks':checks,'new_inference_calls':0,'source':'saved actual HTTP404/200 receipts; same primary collection code; immutable original74'}
    (R/'recovery-D/cpu-tests.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'D_READINESS_CPU_PASS','checks':len(checks),'new_inference_calls':0}))

if __name__=='__main__':main()
