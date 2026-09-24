"""Seal only additive files after CPU and peer receipts; no model operation."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import subprocess

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
BASE_SHA='06c85aae8b6a323a09067725cbf7656fd9cd19df56918c50d95881e0d3284604'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert sha(ROOT/'source-SHA256SUMS')==BASE_SHA
    for line in (ROOT/'source-SHA256SUMS').read_text().splitlines():
        h,rel=line.split('  ',1);assert sha(ROOT/rel)==h,rel
    assert json.loads((ROOT/'continuity/cpu-tests.json').read_text())['status']=='PASS'
    peer=json.loads((ROOT/'preflight/peer-stage.json').read_text())
    assert peer['status']=='PASS' and peer['files_checked']==74 and peer['source_index_sha256']==BASE_SHA
    manifest=json.loads((ROOT/'source-manifest.json').read_text())
    assert all(not Path(v['run_dir']).exists() for v in manifest['runs'].values())
    sources=['mtp_process_v1.py','adapter_llama_continuity_v1.py','window_guards_continuity_v1.py','window_runner_continuity_v1.py','launch_continuity_v1.py']
    files=[ROOT/'sources'/x for x in sources]
    files += [ROOT/'continuity'/x for x in ['ADDENDUM_MTP_PROCESS_OFF_ON.md','addendum.json','mtp-plan.json','config-Q.json','config-MTP.json','prepare_addendum.py','test_addendum.py','cpu-tests.json','freeze_addendum.py']]
    for p in files:
        if p.suffix=='.py':ast.parse(p.read_text())
    runtime=Path(manifest['profiles']['Q']['runtime_source'])
    assert subprocess.check_output(['git','-C',str(runtime),'rev-parse','HEAD'],text=True).strip()==manifest['profiles']['Q']['runtime_revision']
    assert not subprocess.check_output(['git','-C',str(runtime),'diff','--name-only'],text=True).strip()
    evidence={}
    for rel in ['tools/server/server-context.cpp','tools/server/server-schema.cpp','common/arg.cpp','common/speculative.cpp']:
        p=runtime/rel;evidence[rel]={'path':str(p),'sha256':sha(p)}
    evidence['decision']='Same pinned process-level target-only/MTP support. HTTP toggles disabled; no numerical source edits.'
    p=ROOT/'continuity/runtime-static-receipt.json'
    if not p.exists():p.write_text(json.dumps(evidence,indent=2)+'\n')
    files.append(p)
    index=ROOT/'continuity/addendum-SHA256SUMS'
    data=''.join(sha(p)+'  '+str(p.relative_to(ROOT))+'\n' for p in sorted(files))
    if index.exists():assert index.read_text()==data
    else:
        with index.open('x') as f:f.write(data)
    receipt={'status':'PASS','at':datetime.datetime.now().astimezone().isoformat(),'files':len(files),'base_files':74,'base_sha256':BASE_SHA,'addendum_index_sha256':sha(index),'models_started':False}
    p=ROOT/'continuity/freeze-receipt.json'
    if p.exists():assert json.loads(p.read_text())['addendum_index_sha256']==receipt['addendum_index_sha256']
    else:p.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
