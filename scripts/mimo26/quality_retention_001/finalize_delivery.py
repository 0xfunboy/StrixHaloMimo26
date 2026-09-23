"""Post-run delivery verification and metadata. Never starts inference or changes validators."""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO=Path('/home/funboy/StrixHaloMimo26')
ROOT=REPO/'docs/mimo26/quality-retention-001'
sys.path.insert(0,str(ROOT/'sources'))
from common import atomic,now,sha,verify_freeze


def main():
    freeze=verify_freeze(ROOT)
    summary=json.loads((ROOT/'summary.json').read_text())
    assert summary['gates']['EXPERIMENT_COMPLETION']=='COMPLETE'
    assert summary['gates']['REVIEW_REQUIRED']==0
    archive=json.loads((ROOT/'evidence/archive-manifest.json').read_text())
    for rec in archive['files']:
        assert sha(Path(rec['source']))==rec['sha256']==sha(ROOT/rec['copy']),'ORIGINAL_OR_COPY_CHANGED'
    manifest=json.loads((ROOT/'source-manifest.json').read_text())
    for path,expected in manifest['external_lifecycle_hashes'].items():
        assert sha(Path(path))==expected,'RESIDENT_SOURCE_CHANGED'
    verification=ROOT/'verification';verification.mkdir(exist_ok=True)
    cmd=[sys.executable,str(ROOT/'sources/evaluate.py'),'--root',str(ROOT),'--check']
    cp=subprocess.run(cmd,cwd=REPO,text=True,capture_output=True,timeout=90,
                      env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    (verification/'evaluation-check.stdout').write_text(cp.stdout)
    (verification/'evaluation-check.stderr').write_text(cp.stderr)
    assert cp.returncode==0,'FROZEN_EVALUATOR_CHECK_FAILED'
    # Read-only delivery health, distinct from the earlier snapshot consumed by the report.
    controller=manifest['restore']['controller']
    status_cp=subprocess.run([controller,'status'],text=True,capture_output=True,timeout=20,check=True)
    status=json.loads(status_cp.stdout)
    assert status['state']=='READY' and status['release_id']==manifest['restore']['release_id']
    assert status['owner']=='DS41' and status['owner_state']=='RUNNING'
    assert status['paired_backend_http']=='200' and all(x['active'] and x['health_http']=='200' for x in status['ranks'])
    observed=now()
    atomic(ROOT/'delivery-live.json',{'status':'PASS','observed_at':observed,'method':'existing controller status, no generation',
        'controller':status,'note':'Later read-only delivery health; does not rewrite historical restore or earlier final-live timestamps.'})
    # Clarify a derived receipt's timestamp precision without changing any run artifact.
    receipt_path=ROOT/'A-restore-receipt.json'
    receipt=json.loads(receipt_path.read_text())
    if 'residue_check_before_B' in receipt:
        receipt.pop('residue_check_before_B')
        receipt['residue_check_context']='Same MCP call immediately before B dispatch at2026-09-23T13:35:20+02:00; exact ps/lslocks timestamp not separately recorded.'
        atomic(receipt_path,receipt)
    docs=Path('/home/funboy/STRIX_CLUSTER_DOCS')
    docs_paths=['CURRENT.md','projects/mimo26/PROJECT.md','evidence/results/MIMO26_QUALITY_RETENTION_001_2026-09-23.md','archive/CURRENT_PRE_QUALITY_RETENTION_001_2026-09-23.md']
    doc_receipt={p:sha(docs/p) for p in docs_paths}
    atomic(ROOT/'cluster-docs-update.json',{'status':'FINAL_CHECKPOINT_UPDATED','at':observed,
        'directory':str(docs),'sha256':doc_receipt,
        'note':'The earlier in-flight compound update was blocked; final terminal documentation was later written successfully using explicit scoped operations. No DS41 code/release changed.'})
    prep=json.loads((ROOT/'preparation.json').read_text())
    checks={'schema':'mimo26-quality-delivery-verification-v1','verified_at':observed,
        'source_freeze':freeze,'original_run_artifacts_unchanged':len(archive['files']),
        'byte_identical_archived_files':len(archive['files']),
        'resident_lifecycle_files_unchanged':len(manifest['external_lifecycle_hashes']),
        'frozen_evaluator_recomputed':'PASS','frozen_evaluator_command':cmd,
        'check_stdout_sha256':sha(verification/'evaluation-check.stdout'),
        'preparation_commit':prep['preparation_commit'],'paired_evaluable_cases':summary['evaluable_pairs'],
        'peer_rank1_crosscheck':summary['arms']['B']['peer_crosscheck']['status'],
        'report_sha256':sha(ROOT/'REPORT.md'),'summary_sha256':sha(ROOT/'summary.json'),
        'source_index_sha256':sha(ROOT/'source-SHA256SUMS'),
        'new_gpu_calls_during_verification':0,'push_or_deployment':False,
        'packaging_scripts_role':'Posthoc delivery metadata only, not preregistered inference collectors or modified scoring rules.'}
    atomic(ROOT/'verification.json',checks)
    registry={'campaign':'QUALITY-RETENTION-001','phase':'TERMINAL_COMPLETE','updated_at':observed,
        'preparation_commit':prep['preparation_commit'],'source_index_sha256':sha(ROOT/'source-SHA256SUMS'),
        'gates':summary['gates'],'pair_counts':summary['pair_counts'],
        'run_A':manifest['runs']['A']['run_id'],'run_B':manifest['runs']['B']['run_id'],
        'next_exact_action':'Deliver verified results and preserve all artifacts and K2. No new GPU work, retries, tuning, deployment or push authorized.'}
    atomic(ROOT/'registry.json',registry)
    handoff='''# QUALITY-RETENTION-001 — consegna terminale

PHASE: TERMINAL_COMPLETE
LAST_DELIVERY_HEALTH_AT: {observed}
REPO: /home/funboy/StrixHaloMimo26
BRANCH: perf/mimo26-strix
ENTRY_COMMIT: fb432c37f96c4514e763bb49f57614d9696efe79
PREPARATION_COMMIT: {prep}
SOURCE_INDEX_SHA256: {index}
DELIVERY_COMMIT: the local commit containing this handoff; read git log for its exact ID. No circular self-reference.

## Risultati verificati

A mixed21/24 PASS (2 FAIL_SEMANTIC,1 FAIL_FORMAT). B originale21/24 PASS (3 FAIL_SEMANTIC).
20 BOTH_PASS;2 BOTH_FAIL;1 A_FAIL_B_PASS (REASON-03);1 A_PASS_B_FAIL (DOC-03).
Tutte le24 coppie valutabili. Zero cap/incompleti, errori tecnici, validator bloccati o violazioni critiche preregistrate osservate.
SOURCE_FREEZE=PASS; INPUT_COMPARABILITY=PASS; SANITY_PREFLIGHT/POSTFLIGHT=PASS_BOTH; EXPERIMENT_COMPLETION=COMPLETE.
GENERAL_QUALITY_EQUIVALENCE=NOT_ESTABLISHED; QUANTIZATION_ONLY_EFFECT=NOT_ISOLATED.
LONG_CONTEXT/CONCURRENCY/MTP_DFLASH=NOT_EVALUATED; PRODUCTION_PROMOTION=NOT_PERFORMED.

REASON-03: A calcola correttamente ma usa total_censes invece di total_cents; schema non riparato.
DOC-03: B classifica correttamente NOT_RUN ma omette la citazione E3 richiesta.
REASON-02: A scelta ammissibile subottimale; B supera il budget.
REASON-04: entrambi perdono il tie-break sul rischio e dichiarano il costo del percorso errato.
Dettagli in FINDINGS.md e nelle coppie canoniche, senza adattamento dei validator dopo i risultati.

## Run e restore

A: /home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-A-mixed-001
B: /home/funboy/.local/state/strixhalomimo26/windows/quality-retention-001-B-original-001
Entrambi: un solo caricamento,24 casi+6 sanity pre+6 post,36 record primari, worker exit0, NORMAL_COMPLETION.
A restore PASS2026-09-23T13:33:46+02:00. B restore PASS2026-09-23T13:55:22+02:00.
K2 dspark-k2-gfx1151 release5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513, DS41/RUNNING epoch1790164228979629195, rank0/rank1/paired HTTP200.
I processi vLLM EngineCore superstiti appartengono ai cgroup DS41 residenti, non a residui MiMo. Own worker/supervisor inattivi e PID modelli precedenti assenti; lock liberi nel controllo registrato. Non fermare K2.
Timestamp e perimetri distinti in final-live.json; ultima health read-only in delivery-live.json.

## Artefatti / verifica

ROOT: /home/funboy/StrixHaloMimo26/docs/mimo26/quality-retention-001/
PROTOCOL.md,cases.jsonl,expected.jsonl,sanity.jsonl,source-manifest.json,sources/,source-SHA256SUMS: preregistrati e invariati.
REPORT.md,summary.json,paired-results.jsonl,raw-results.jsonl: generati dal valutatore congelato; raw-results è indice derivato dichiarato.
FINDINGS.md: interpretazione degli errori, non nuovo validator.
evidence/:276 copie byte-identiche di artefatti originali, manifest/hash, raw rank1 peer verificato.
verification.json e verification/evaluation-check.stdout: ricalcolo CPU PASS, originali e release sources invariati.
cluster-docs-update.json: checkpoint globale finale aggiornato; vecchio CURRENT preservato in archivio.
I due script di packaging posthoc non cambiano preregistrazione, risposte o scoring.

Comando effettivamente verificato:

```bash
cd /home/funboy/StrixHaloMimo26
PYTHONDONTWRITEBYTECODE=1 python3 docs/mimo26/quality-retention-001/sources/evaluate.py --root docs/mimo26/quality-retention-001 --check
```

Il comando non genera token: ricalcola i verdict sui raw esistenti e usa il sandbox Podman isolato già verificato per il codice. Richiede i percorsi originali presenti su NODE01 e l'immagine locale pinned. Nessuna pretesa di portabilità su una macchina priva di tali evidenze.

## NEXT EXACT ACTION

Consegnare questi risultati, preservare raw, sorgenti e K2. Nessun nuovo run, replay, tuning, deployment o push è autorizzato. Un nuovo holdout realistico è soltanto proposto in FINDINGS.md e richiede mandato separato. PERF-BASELINE-001 resta terminale PARTIAL_ENGINE_DECODE_ONLY; non riaprire le sue lacune storiche.
'''.format(observed=observed,prep=prep['preparation_commit'],index=sha(ROOT/'source-SHA256SUMS'))
    (ROOT/'HANDOFF.md').write_text(handoff)
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name!='DELIVERY-SHA256SUMS')
    for p in files:assert not p.is_symlink()
    (ROOT/'DELIVERY-SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(ROOT))+'\n' for p in files))
    for line in (ROOT/'DELIVERY-SHA256SUMS').read_text().splitlines():
        expected,rel=line.split('  ',1);assert sha(ROOT/rel)==expected
    print(json.dumps({'status':'DELIVERY_FINALIZATION_PASS','delivery_files_hashed':len(files),
        'original_files_unchanged':len(archive['files']),'source_freeze_files':freeze['files_checked'],
        'gates':summary['gates'],'last_health_at':observed,'controller':status},indent=2))

if __name__=='__main__':main()
