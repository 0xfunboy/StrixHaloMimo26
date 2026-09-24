#!/usr/bin/env python3
"""Fetch only preregistered public files, with bounded resume and integrity checks."""
from __future__ import annotations
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

ROOT = Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
WEIGHTS = Path('/home/funboy/models/gguf/qwen38-flash-next-agenticrequant')
RESERVE = 60 * 2**30
ALLOWANCE = 12 * 2**30
LIMIT = 110 * 2**30


def now():
    return datetime.datetime.now().astimezone().isoformat()


def atomic(path, obj):
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def digest(path, algo='sha256'):
    h = hashlib.new(algo)
    if algo == 'sha1':
        h.update(b'blob ' + str(path.stat().st_size).encode() + b'\x00')
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def selected(mode):
    if mode == 'weights':
        m = json.loads((ROOT / 'upstream/qwen-acquisition-manifest.json').read_text())
        assert sum(x['size'] for x in m['files']) <= LIMIT
        return m['files']
    items = []
    for label in ('qwen-target', 'qwen-mtp', 'qwen-official'):
        d = json.loads((ROOT / 'upstream' / (label + '-selected.json')).read_text())
        allowed = {'README.md'} if label != 'qwen-official' else {
            'README.md', 'LICENSE', 'chat_template.jinja', 'tokenizer_config.json',
            'tokenizer.json', 'config.json', 'generation_config.json'}
        for f in d['files']:
            if f['rfilename'] not in allowed:
                continue
            items.append({'repository': d['repository'], 'revision': d['revision'],
                          'filename': f['rfilename'], 'size': f['size'],
                          'sha256': f.get('lfs', {}).get('sha256'), 'git_blob_sha1': f.get('blobId'),
                          'destination': str(ROOT / 'upstream' / label / f['rfilename'])})
    return items


def verify(path, entry):
    assert path.stat().st_size == entry['size'], 'FILE_SIZE_MISMATCH:' + entry['filename']
    value = digest(path)
    if entry.get('sha256'):
        assert value == entry['sha256'], 'FILE_SHA256_MISMATCH:' + entry['filename']
    else:
        assert digest(path, 'sha1') == entry['git_blob_sha1'], 'GIT_BLOB_MISMATCH:' + entry['filename']
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('small', 'weights'))
    args = ap.parse_args()
    mode = args.mode
    lock = (ROOT / 'preflight' / ('acquire-' + mode + '.lock')).open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    receipt = ROOT / 'preflight' / ('acquire-' + mode + '.json')
    if receipt.exists():
        raise SystemExit('Existing acquisition receipt: reconcile before an explicit resume')
    entries = selected(mode)
    if mode == 'weights':
        remaining = sum(x['size'] - (Path(x['destination'] + '.part').stat().st_size
                            if Path(x['destination'] + '.part').exists() else 0)
                        for x in entries if not Path(x['destination']).exists())
        fs = os.statvfs('/home/funboy')
        assert fs.f_bavail * fs.f_frsize - remaining - ALLOWANCE >= RESERVE, 'BLOCKED_ACQUISITION_SPACE'
    state = {'campaign': 'STRIX-GENERALIST-SELECTION-001', 'mode': mode, 'status': 'IN_FLIGHT',
             'pid': os.getpid(), 'started_at': now(), 'files': [], 'weight_limit_bytes': LIMIT}
    atomic(receipt, state)
    deadline = time.monotonic() + (21000 if mode == 'weights' else 300)
    try:
        for entry in entries:
            dest = Path(entry['destination'])
            assert dest.is_relative_to(WEIGHTS if mode == 'weights' else ROOT / 'upstream')
            assert len(entry['revision']) == 40 and '/' not in entry['filename']
            dest.parent.mkdir(parents=True, exist_ok=True)
            row = {'filename': entry['filename'], 'destination': str(dest), 'size': entry['size'],
                   'revision': entry['revision'], 'status': 'VERIFYING' if dest.exists() else 'TRANSFERRING'}
            state['files'].append(row)
            if dest.exists():
                row.update(status='EXISTING_VERIFIED', sha256=verify(dest, entry))
                atomic(receipt, state)
                continue
            part = dest.with_name(dest.name + '.part')
            url = 'https://huggingface.co/' + entry['repository'] + '/resolve/' + entry['revision'] + '/' + entry['filename']
            for attempt in range(1, 6):
                offset = part.stat().st_size if part.exists() else 0
                assert 0 <= offset <= entry['size'], 'INVALID_PARTIAL_SIZE'
                if offset == entry['size']:
                    break
                assert time.monotonic() < deadline, 'ACQUISITION_DEADLINE'
                row.update(attempt=attempt, bytes_present=offset, updated_at=now())
                atomic(receipt, state)
                headers = {'User-Agent': 'Strix-Generalist-Selection/1.0'}
                if offset:
                    headers['Range'] = 'bytes=' + str(offset) + '-'
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=45) as response:
                        if offset:
                            assert response.status == 206 and response.headers.get('Content-Range', '').startswith('bytes ' + str(offset) + '-'), 'RESUME_RANGE_NOT_HONORED'
                        else:
                            assert response.status == 200, 'UNEXPECTED_HTTP_STATUS'
                        last_recorded = offset
                        with part.open('ab' if part.exists() else 'xb') as f:
                            while True:
                                if time.monotonic() > deadline:
                                    raise TimeoutError('acquisition wall deadline')
                                data = response.read(8 * 1024 * 1024)
                                if not data:
                                    break
                                if offset + len(data) > entry['size']:
                                    raise ValueError('server exceeded declared file size')
                                if mode == 'weights':
                                    fs = os.statvfs(dest.parent)
                                    if fs.f_bavail * fs.f_frsize < RESERVE + ALLOWANCE:
                                        raise RuntimeError('BLOCKED_ACQUISITION_FREE_SPACE_DROPPED')
                                f.write(data)
                                offset += len(data)
                                if offset - last_recorded >= 64 * 1024 * 1024:
                                    f.flush()
                                    row.update(bytes_present=offset, updated_at=now())
                                    atomic(receipt, state)
                                    last_recorded = offset
                            f.flush()
                            os.fsync(f.fileno())
                    if offset == entry['size']:
                        break
                    raise ConnectionError('truncated transfer; resume the same file only')
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                    row['last_network_error'] = type(exc).__name__ + ': ' + str(exc)[:500]
                    atomic(receipt, state)
                    if attempt == 5:
                        raise
                    time.sleep(3)
            value = verify(part, entry)
            os.link(part, dest)  # publish without overwriting another file
            part.unlink()
            row.update(status='VERIFIED', sha256=value, bytes_present=entry['size'], completed_at=now())
            atomic(receipt, state)
            print(json.dumps({'file': entry['filename'], 'status': row['status'], 'sha256': value}), flush=True)
        state.update(status='PASS', finished_at=now())
        atomic(receipt, state)
        return 0
    except Exception as exc:
        state.update(status='BLOCKED', error=type(exc).__name__ + ': ' + str(exc)[:1500], finished_at=now())
        atomic(receipt, state)
        print(json.dumps({'status': 'BLOCKED', 'error': state['error']}), flush=True)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
