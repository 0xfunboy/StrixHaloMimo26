"""Post-evaluation packaging only. Does not alter frozen sources or original run files."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/mimo26/quality-retention-001')
RUNS=Path('/home/funboy/.local/state/strixhalomimo26/windows')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    records=[]
    for arm,suffix in [('A','A-mixed'),('B','B-original')]:
        source=RUNS/('quality-retention-001-'+suffix+'-001')
        result=json.loads((source/'result.json').read_text())
        assert result['run_completion']=='PASS' and result['cleanup']['status']=='PASS','NOT_TERMINAL_RESTORED'
        destination=ROOT/'evidence'/('run-'+arm)
        for p in sorted(source.rglob('*')):
            if p.is_symlink():raise ValueError('unexpected symlink '+str(p))
            if not p.is_file():continue
            if p.name in ('run.lock','compute-lock-held'):continue
            if p.suffix not in ('.json','.jsonl','.txt','.log','.stdout','.stderr') and p.name!='frozen-SHA256SUMS':
                raise ValueError('unreviewed run artifact '+str(p))
            before=sha(p);rel=p.relative_to(source);target=destination/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():assert sha(target)==before,'EXISTING_COPY_DIFFERS_DO_NOT_OVERWRITE'
            else:
                with target.open('xb') as f:f.write(p.read_bytes())
            assert sha(p)==before==sha(target),'SOURCE_CHANGED_DURING_COPY'
            records.append({'arm':arm,'source_node':'01-EVO-X3','source':str(p),
                            'copy':str(target.relative_to(ROOT)),'sha256':before,'bytes':p.stat().st_size})
    manifest={'schema':'mimo26-quality-posthoc-archive-v1','role':'BYTE_IDENTICAL_COPIES_OF_TERMINAL_RUN_ARTIFACTS_NOT_NEW_EXPERIMENT',
              'originals_modified':False,'frozen_protocol_modified':False,'files':records}
    out=ROOT/'evidence/archive-manifest.json'
    text=json.dumps(manifest,indent=2)+'\n'
    if out.exists():assert json.loads(out.read_text())==manifest,'EXISTING_ARCHIVE_MANIFEST_DIFFERS'
    else:out.write_text(text)
    (ROOT/'evidence/original-SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['source']+'\n' for r in records))
    print(json.dumps({'status':'NATIVE_EVIDENCE_ARCHIVE_PASS','files':len(records),
          'bytes':sum(r['bytes'] for r in records),'source_unchanged':True,'manifest_sha256':sha(out)}))

if __name__=='__main__':main()
