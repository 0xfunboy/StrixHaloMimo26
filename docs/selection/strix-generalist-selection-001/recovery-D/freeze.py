"""Freeze the one D readiness correction; leave every prior freeze untouched."""
from pathlib import Path
import ast
import json
import hashlib
from datetime import datetime
R=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
HERE=R/'recovery-D'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for index in [R/'source-SHA256SUMS',R/'continuity/addendum-SHA256SUMS']:
        for line in index.read_text().splitlines():
            h,name=line.split('  ',1);assert sha(R/name)==h,name
    tests=json.loads((HERE/'cpu-tests.json').read_text());assert tests['status']=='PASS'
    plan=json.loads((HERE/'manifest.json').read_text());assert not Path(plan['run']['run_dir']).exists()
    files=[R/'sources'/name for name in ['d_readiness_recovery_v1.py','adapter_ds41_readiness_v1.py','window_guards_d_readiness_v1.py','window_runner_d_readiness_v1.py','launch_d_readiness_v1.py']]
    files += [HERE/name for name in ['manifest.json','config-D.json','prepare.py','test_cpu.py','cpu-tests.json','PROTOCOL.md','setup-evidence.json','freeze.py']]
    for p in files:
        if p.suffix=='.py':ast.parse(p.read_text())
    data=''.join(sha(p)+'  '+str(p.relative_to(R))+'\n' for p in sorted(files))
    index=HERE/'source-SHA256SUMS'
    if index.exists():assert index.read_text()==data
    else:
        with index.open('x') as f:f.write(data)
    result={'status':'PASS','at':datetime.now().astimezone().isoformat(),'files':len(files),'base_index_sha256':sha(R/'source-SHA256SUMS'),
            'recovery_index_sha256':sha(index),'new_run_dispatched':False,'primary_input_sha256':sha(R/'requests-D.jsonl')}
    (HERE/'freeze-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
