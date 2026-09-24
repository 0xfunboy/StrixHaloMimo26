"""Read selected archived Qwen reports; preserve old archives and frozen campaign."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import tarfile

ROOT = Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
REPO = ROOT.parents[2]
OUT = ROOT / 'continuity'
COMMIT = '87442a8e1b999e5f33165d0b6b563eac5248ab15'
ARCHIVE = Path('/home/funboy/StrixHaloClusterGLM/archives/research-node01-20260910.tar.zst')
CAMPAIGNS = ['QWEN-FLASH-NEXT-SINGLE-NODE-001', 'QWEN-QUAL-001', 'QWEN-IQ3-SPEED-001', 'QWEN-IQ3-QUALITY-002']
SELECT = {'RESULT.md', 'C1-RESULT-TABLE.md', 'C2-RESULT-TABLE.md', 'C2-RESIDUAL-BLOCKER.md', 'c1-long-crossmode-verdict.json', 'CLUSTER-HANDOFF.md', 'UTILITY-COMPARISON.md', 'audit-results.json', 'manifest.json', 'manifest-sha256.json', 'tokenizer-preflight.json', 'identity.json', 'summary.json'}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f: json.dump(obj, f, ensure_ascii=False, indent=2); f.write('\n')

def main():
    if (OUT/'reconciliation.json').exists():
        print((OUT/'reconciliation.json').read_text()); return
    assert subprocess.check_output(['hostname'], text=True).strip() == '01-EVO-X3'
    index = ROOT/'source-SHA256SUMS'
    git_bytes = subprocess.check_output(['git','-C',str(REPO),'show',COMMIT+':'+str(index.relative_to(REPO))])
    assert index.read_bytes() == git_bytes
    members = []
    for line in index.read_text().splitlines():
        h, rel = line.split('  ', 1); assert sha(ROOT/rel) == h; members.append(rel)
    assert len(members) == 74
    existing = {c: {'archived_members':0, 'raw_named_members':0, 'selected':[]} for c in CAMPAIGNS}
    result = {'at':datetime.datetime.now().astimezone().isoformat(), 'preparation_commit':COMMIT,
              'source_index_sha256':sha(index), 'frozen_files_verified':74,
              'erratum':'Prior final-answer SHA 06c85aae227c3c2d242a44a2c402a724e300f068540a149ec533cfa97640cd8c was a transcription error; disk index is byte-identical to Git preparation commit. Original freeze unchanged.',
              'history':existing, 'archive':str(ARCHIVE), 'archive_exists':ARCHIVE.is_file(), 'new_inference_calls':0}
    if ARCHIVE.is_file():
        result['archive_size'] = ARCHIVE.stat().st_size
        proc = subprocess.Popen(['zstd','-dc','--',str(ARCHIVE)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            with tarfile.open(fileobj=proc.stdout, mode='r|') as tar:
                for member in tar:
                    parts = Path(member.name).parts
                    campaign = next((c for c in CAMPAIGNS if c in parts), None)
                    if campaign is None or not member.isfile(): continue
                    rec = existing[campaign]; rec['archived_members'] += 1
                    if member.name.endswith(('-raw.json','/raw-results.jsonl')): rec['raw_named_members'] += 1
                    tail = Path(*parts[parts.index(campaign)+1:])
                    if tail.name not in SELECT or len(tail.parts)>2 or member.size>4*1024*1024: continue
                    data = tar.extractfile(member).read()
                    dest = OUT/'historical-reports'/campaign/tail
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if dest.exists(): assert dest.read_bytes() == data
                    else:
                        with dest.open('xb') as f: f.write(data)
                    rec['selected'].append({'archive_member':member.name, 'path':str(dest), 'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()})
            proc.stdout.close(); err=proc.stderr.read(); rc=proc.wait(timeout=30)
            if rc: raise RuntimeError('ARCHIVE_READ_FAILED:'+err.decode(errors='replace')[-500:])
        finally:
            if proc.poll() is None: proc.terminate(); proc.wait(timeout=10)
    save(OUT/'reconciliation.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='history'},indent=2))
    print(json.dumps({c:{'members':v['archived_members'],'raw_named_members':v['raw_named_members'],'selected':len(v['selected'])} for c,v in existing.items()},indent=2))

if __name__=='__main__': main()
