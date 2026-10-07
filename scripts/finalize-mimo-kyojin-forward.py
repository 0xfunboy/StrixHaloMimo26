#!/usr/bin/env python3
"""Read-only final verifier for MIMO-KYOJIN-NODE02-INSTALL-001.

It never sends a generation request. It verifies the existing NODE01 private
forward and the already-terminal q18/q19 receipts on NODE02, then writes a
public-safe local receipt in the MiMo coordination repository.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time
import urllib.request

REPO = Path('/home/funboy/StrixHaloMimo26')
ROOT = REPO / 'docs/install/mimo-kyojin-node02-install-001'
EVIDENCE = ROOT / 'evidence'
REMOTE = '02-evo-x3-tb'
REMOTE_DEPLOYMENT = '/home/funboy/StrixHaloMimoKyojin'
REMOTE_STATE = '/home/funboy/.local/state/strixhalomimokyojin'
UNIT = 'mimo-kyojin-forward-node02.service'


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=check)


def ssh(command: str) -> str:
    return run(['ssh', '-o', 'IdentityAgent=none', '-o', 'BatchMode=yes',
                REMOTE, command]).stdout


def atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def unit(name: str) -> dict:
    raw = run(['systemctl', '--user', 'show', name, '-p', 'ActiveState',
               '-p', 'SubState', '-p', 'MainPID', '-p', 'InvocationID',
               '-p', 'NRestarts', '-p', 'Result']).stdout
    return dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)


def get(path: str):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return json.load(opener.open('http://127.0.0.1:18571' + path, timeout=8))


def main() -> None:
    state = unit(UNIT)
    if state['ActiveState'] != 'active' or state['SubState'] != 'running':
        raise SystemExit(f'private forward is not active: {state}')
    health = get('/health')
    models = get('/v1/models')
    slots = get('/slots')
    if health.get('status') != 'ok' or health.get('ctx') != 40960:
        raise SystemExit(f'unexpected health: {health}')
    if models['data'][0]['id'] != 'mimo-mopd-kyojin':
        raise SystemExit(f'unexpected model identity: {models}')
    if any(x.get('is_processing') for x in slots):
        raise SystemExit(f'MiMo is busy: {slots}')

    q18 = json.loads(ssh(
        f'cat {REMOTE_STATE}/qualification-001-final/requests/'
        'q18-final-forward/result.json'))
    q19 = json.loads(ssh(
        f'cat {REMOTE_STATE}/qualification-001-final/requests/'
        'q19-node01-client/result.json'))
    ledger = json.loads(ssh(f'cat {REMOTE_STATE}/ledger.json'))
    remote_commit = ssh(
        f'git -C {REMOTE_DEPLOYMENT} rev-parse HEAD').strip()
    remote_status = ssh(
        f'git -C {REMOTE_DEPLOYMENT} status --short --branch').strip()

    assert q18['status'] == 'COMPLETE' and q18['exact'] is True
    assert q18['response']['choices'][0]['message']['content'] == 'FORWARD_READY'
    assert q19['status'] == 'COMPLETE' and q19['exact'] is True
    assert q19['content'] == 'CLIENT_READY'
    assert ledger['phase'] == 'COMPLETE'
    assert not [x for x in ledger['requests'] if x['state'] == 'IN_FLIGHT']

    receipt = {
        'schema': 'mimo-kyojin-node01-forward-final-v1',
        'status': 'PASS',
        'observed_at': time.time(),
        'unit': state,
        'health': health,
        'models': models,
        'slots': slots,
        'q18': {'status': q18['status'], 'exact': q18['exact'],
                'content': q18['response']['choices'][0]['message']['content'],
                'usage': q18['response']['usage'],
                'timings': q18['response']['timings']},
        'q19': {'status': q19['status'], 'exact': q19['exact'],
                'content': q19['content'], 'usage': q19['usage'],
                'timings': q19['timings']},
        'remote_commit': remote_commit,
        'remote_git_status': remote_status,
        'ledger': {'phase': ledger['phase'], 'starts': len(ledger['starts']),
                   'requests': len(ledger['requests']),
                   'charged_output_tokens': ledger['charged_output_tokens']},
        'generation_requests_sent_by_this_verifier': 0,
    }
    atomic(EVIDENCE / 'NODE01_FORWARD_LIVE.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
