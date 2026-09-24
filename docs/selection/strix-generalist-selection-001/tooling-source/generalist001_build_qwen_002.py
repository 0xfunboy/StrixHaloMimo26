#!/usr/bin/env python3
"""One bounded, resumable source build; never starts a model or installs globally."""
from __future__ import annotations
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
BASE = Path('/home/funboy/ai-exp/strix-generalist-selection-001')
REV = 'ba5354d46ca63e8225c28e1331f0f7651723ad05'

def now():
    return datetime.datetime.now().astimezone().isoformat()

def atomic(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def main():
    lock = (ROOT / 'preflight/qwen-build.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    receipt = ROOT / 'preflight/qwen-build-002.json'
    if receipt.exists():
        raise SystemExit('Existing build receipt: reconcile it instead of launching again')
    head = subprocess.check_output(['git', '-C', str(BASE / 'qwen-runtime'), 'rev-parse', 'HEAD'], text=True).strip()
    assert head == REV
    cmd = ['cmake', '--build', str(BASE / 'qwen-build'), '--target', 'llama-server', 'llama-tokenize', '-j', '3']
    state = {'status': 'IN_FLIGHT', 'pid': os.getpid(), 'started_at': now(), 'source_revision': REV,
             'command': cmd, 'no_inference': True, 'global_install': False}
    atomic(receipt, state)
    with (ROOT / 'preflight/qwen-build-002.log').open('x') as log:
        try:
            cp = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=1740,
                                env={**os.environ, 'CMAKE_BUILD_PARALLEL_LEVEL': '3'})
            state.update(status='PASS' if cp.returncode == 0 else 'FAIL', returncode=cp.returncode)
        except Exception as exc:
            state.update(status='FAIL', error=type(exc).__name__ + ': ' + str(exc))
    state['finished_at'] = now()
    if state['status'] == 'PASS':
        state['binaries'] = {}
        for p in sorted((BASE / 'qwen-build/bin').glob('*')):
            if p.is_file() and not p.is_symlink():
                state['binaries'][str(p)] = {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    atomic(receipt, state)
    print(json.dumps(state, indent=2))
    return 0 if state['status'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
