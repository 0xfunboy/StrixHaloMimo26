"""CPU-only terminal delivery. No model, service mutation, retry, or Git push."""
from __future__ import annotations
import argparse
import base64
import collections
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
sys.path.insert(0, str(ROOT / 'sources'))
from common import atomic, now, sha, read_jsonl
from window_guards import SSH, unit_state
from mtp_process_v1 import verify_addendum
from d_readiness_recovery_v1 import effective_manifest, verify_recovery
import finalize as base_finalize


def effective(root: Path) -> dict:
    manifest = effective_manifest(root, json.loads((root / 'source-manifest.json').read_text()))
    manifest['runs']['Q']['config'] = 'continuity/config-Q.json'
    manifest['runs']['D_SETUP'] = json.loads((root / 'recovery-D/manifest.json').read_text())['prior_run']
    return manifest


def require_terminal(manifest: dict) -> dict:
    found = {}
    for profile, info in manifest['runs'].items():
        run = Path(info['run_dir'])
        unit = unit_state(info['supervisor_unit'])
        if unit.get('ActiveState') not in ('inactive', 'failed') or int(unit.get('MainPID', '0')):
            raise RuntimeError('RUN_OR_RESTORE_STILL_ACTIVE:' + profile)
        result = json.loads((run / 'result.json').read_text())
        if result.get('run_completion') not in ('PASS', 'FAILED', 'INTERRUPTED', 'TIMEOUT', 'BLOCKED'):
            raise RuntimeError('NO_TERMINAL_RECEIPT:' + profile)
        if result.get('cleanup', {}).get('status') != 'PASS':
            raise RuntimeError('RESTORE_NOT_PASS:' + profile)
        found[profile] = {'run_id': run.name, 'completion': result['run_completion'],
                          'cleanup': result['cleanup'], 'supervisor': unit}
    return found


def store_copy(source: str, dest: Path, data: bytes, node: str, rows: list) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if dest.read_bytes() != data:
            raise RuntimeError('EXISTING_ARCHIVE_DIFFERS:' + str(dest))
    else:
        with dest.open('xb') as handle:
            handle.write(data)
    rows.append({'node': node, 'source': source, 'copy': str(dest), 'sha256': sha(dest), 'bytes': len(data)})


def peer_files(run: Path) -> list:
    # Fixed read-only subtree; refuse links, special files, or unexpectedly large data.
    program = '''from pathlib import Path
import base64,hashlib,json
root=Path(RUN_PATH)
assert str(root).startswith('/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-')
files=[];total=0
for p in sorted(root.rglob('*')):
 if not p.is_file() or p.is_symlink() or p.name.endswith('.lock') or p.name=='compute-lock-held':continue
 assert p.resolve().is_relative_to(root.resolve())
 total+=p.stat().st_size
 if total>128*1024*1024:raise RuntimeError('BOUNDED_PEER_ARCHIVE_TOO_LARGE')
 b=p.read_bytes();files.append({'relative':str(p.relative_to(root)),'sha256':hashlib.sha256(b).hexdigest(),'data':base64.b64encode(b).decode()})
print(json.dumps(files))
'''.replace('RUN_PATH', repr(str(run)))
    proc = subprocess.run(SSH + ['/usr/bin/python3 -c ' + shlex.quote(program)], capture_output=True, timeout=90)
    if proc.returncode:
        raise RuntimeError('PEER_READ_FAILED:' + proc.stderr.decode()[-1000:])
    return json.loads(proc.stdout)


def archive(root: Path, manifest: dict) -> dict:
    rows = []
    for profile, info in manifest['runs'].items():
        run = Path(info['run_dir'])
        for path in sorted(run.rglob('*')):
            if not path.is_file() or path.is_symlink() or path.name.endswith('.lock') or path.name == 'compute-lock-held':
                continue
            if path.stat().st_size > 128 * 1024 * 1024:
                raise RuntimeError('UNEXPECTED_LARGE_RUN_ARTIFACT:' + str(path))
            before = sha(path)
            store_copy(str(path), root / 'evidence' / ('run-' + profile) / path.relative_to(run), path.read_bytes(), 'NODE01', rows)
            if sha(path) != before or rows[-1]['sha256'] != before:
                raise RuntimeError('SOURCE_CHANGED_DURING_COPY:' + str(path))
        if profile in ('D', 'D_SETUP', 'O'):
            for item in peer_files(run):
                relative = Path(item['relative'])
                if relative.is_absolute() or '..' in relative.parts:
                    raise RuntimeError('UNSAFE_PEER_RELATIVE_PATH')
                dest = root / 'evidence' / ('peer-' + profile) / relative
                if profile == 'O' and str(relative) == 'rank1-raw-results.jsonl':
                    dest = root / 'evidence/O-rank1-raw-results.jsonl'
                store_copy(str(run / relative), dest, base64.b64decode(item['data'], validate=True), 'NODE02', rows)
                if rows[-1]['sha256'] != item['sha256']:
                    raise RuntimeError('PEER_COPY_HASH_MISMATCH')
    receipt = {'status': 'PASS', 'at': now(), 'files': rows, 'count': len(rows),
               'counts_by_node': dict(collections.Counter(item['node'] for item in rows)),
               'note': 'Byte-identical copies. Missing arm-result for blocked preflight is not manufactured.'}
    atomic(root / 'evidence/archive-manifest.json', receipt)
    (root / 'evidence/original-NODE01-SHA256SUMS').write_text(''.join(x['sha256'] + '  ' + x['source'] + '\n' for x in rows if x['node'] == 'NODE01'))
    return receipt


def prefix_audit(root: Path, manifest: dict) -> dict:
    result = {}
    for profile in ('Q', 'M', 'D', 'O'):
        run = Path(manifest['runs'][profile]['run_dir'])
        rows = read_jsonl(run / 'raw-results.jsonl')
        plans = read_jsonl(root / ('requests-' + profile + '.jsonl'))
        keys = lambda rs: [(x['phase'], x['request_key']) for x in rs]
        if keys(rows) != keys(plans[:len(rows)]) or len(set(keys(rows))) != len(rows):
            raise RuntimeError('NON_FROZEN_OR_DUPLICATE_PREFIX:' + profile)
        intents = list((run / 'requests').glob('*/intent.json'))
        pending = [str(p.parent) for p in intents if not (p.parent / 'result.json').exists()]
        if pending or len(intents) != len(rows):
            raise RuntimeError('UNRECONCILED_PRIMARY_REQUEST:' + profile)
        result[profile] = {'status': 'PASS_FOR_RECORDED_PREFIX', 'records': len(rows), 'intents': len(intents),
                           'phases': dict(collections.Counter(x['phase'] for x in rows)), 'pending_requests': pending}
    local = read_jsonl(Path(manifest['runs']['O']['run_dir']) / 'raw-results.jsonl')
    peer = read_jsonl(root / 'evidence/O-rank1-raw-results.jsonl')
    fields = ['phase', 'request_key', 'input_token_ids', 'output_token_ids', 'final_text', 'reasoning_text', 'finish_reason', 'completion_status', 'source_index_sha256']
    if len(peer) != len(local) or any(any(a.get(k) != b.get(k) for k in fields) for a, b in zip(local, peer)):
        raise RuntimeError('O_RECORDED_PREFIX_RANK_MISMATCH')
    result['O_peer'] = {'status': 'PASS_FOR_ALL_RECORDED_REQUESTS', 'records_per_rank': len(peer),
                        'not_extra_replicas': True, 'full_32_request_campaign': len(peer) == 32}
    atomic(root / 'delivery/request-prefix-audit.json', result)
    return result


def close(root: Path) -> dict:
    extension = verify_addendum(root)
    recovery = verify_recovery(root)
    manifest = effective(root)
    terminal = require_terminal(manifest)
    live = base_finalize.final_live(root, manifest)
    preserved = base_finalize.check_preserved(root)
    archive_receipt = archive(root, manifest)
    prefixes = prefix_audit(root, manifest)
    # The actual frozen scorer remains authoritative; this wrapper changes no verdict.
    for action in ('--write', '--check'):
        cmd = ['/usr/bin/python3', str(root / 'continuity/evaluate_continuity.py'), '--root', str(root), action]
        import os
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                              env={**os.environ, 'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1'})
        stem = 'cpu-' + action.removeprefix('--')
        (root / 'delivery' / (stem + '.stdout')).write_text(proc.stdout)
        (root / 'delivery' / (stem + '.stderr')).write_text(proc.stderr)
        if proc.returncode:
            raise RuntimeError('CPU_RECALCULATION_FAILED:' + action + ':' + proc.stderr[-1800:])
    for item in archive_receipt['files']:
        if sha(item['copy']) != item['sha256'] or (item['node'] == 'NODE01' and sha(item['source']) != item['sha256']):
            raise RuntimeError('ARCHIVE_CHANGED_AFTER_EVALUATION')
    receipt = {'status': 'PASS', 'at': now(), 'workflow': 'AUTHORIZED_WINDOWS_TERMINAL_WITH_BLOCKERS',
               'experiment_collection': 'PARTIAL_OR_BLOCKED', 'source_freeze': extension, 'readiness_recovery': recovery,
               'terminal_runs': terminal, 'prefix_audit': prefixes, 'preserved': preserved,
               'archived_files': archive_receipt['count'], 'archive_counts_by_node': archive_receipt['counts_by_node'],
               'CPU_RECALCULATION_CHECK': 'CONTINUITY_EVALUATION_CHECK_PASS', 'final_live': live['observed_at'],
               'new_inference_calls_in_delivery': 0, 'model_actions_in_delivery': 0,
               'limitations': 'M/O stopped at separate frozen sanity gates; MTP lacks OFF references. No retries or invented panel results.'}
    atomic(root / 'verification.json', receipt)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    result = close(args.root.resolve())
    print(json.dumps({k: result[k] for k in ('status', 'at', 'workflow', 'experiment_collection', 'preserved', 'archived_files', 'archive_counts_by_node', 'CPU_RECALCULATION_CHECK')}, indent=2))
