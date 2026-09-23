#!/usr/bin/env python3
from __future__ import annotations
import ast
import json
import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

from perf_measure_common import StreamMeasure, append_jsonl, atomic_json, system_snapshot

RUN = Path(os.environ['MIMO26_RUN_DIR'])
SERVER = os.environ['MIMO26_LLAMA_SERVER']
MODEL = os.environ['MIMO26_GGUF_FIRST_SHARD']
WORKLOADS = Path(os.environ['MIMO26_WORKLOADS'])
PORT = int(os.environ.get('MIMO26_PORT', '18341'))
LOAD_TIMEOUT = float(os.environ.get('MIMO26_LOAD_TIMEOUT', '600'))
AMD_SMI = os.environ.get('MIMO26_AMD_SMI', '')
HOST = '127.0.0.1'
BASE = 'http://%s:%d' % (HOST, PORT)
LOG = RUN / 'server.log'
RUN.mkdir(parents=True, exist_ok=True)
doc = json.loads(WORKLOADS.read_text())
workloads = doc['workloads']
target_out = int(doc['sampling']['max_output_tokens'])
os.environ['MIMO26_AMD_SMI'] = AMD_SMI

def req(path, payload=None, timeout=10):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers['Content-Type'] = 'application/json'
    r = urllib.request.Request(
        BASE + path,
        data=data,
        headers=headers,
        method='POST' if data is not None else 'GET',
    )
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        body = resp.read()
        return resp.status, json.loads(body) if body else None

def code_gate(text):
    code = text.strip()
    fence = chr(96) * 3
    if code.startswith(fence):
        lines = code.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == fence:
            lines = lines[:-1]
        code = '\n'.join(lines)
        if code.lstrip().startswith('python\n'):
            code = code.lstrip()[7:]
    try:
        tree = ast.parse(code)
    except Exception as e:
        return False, 'parse:%s:%s' % (type(e).__name__, e)
    forbidden = (
        ast.Import, ast.ImportFrom, ast.Attribute, ast.With, ast.AsyncWith,
        ast.ClassDef, ast.Lambda, ast.Global, ast.Nonlocal, ast.Delete,
        ast.Try, ast.Raise, ast.While,
    )
    if any(isinstance(n, forbidden) for n in ast.walk(tree)):
        return False, 'forbidden_ast'
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(funcs) != 1 or funcs[0].name != 'clamp':
        return False, 'missing_clamp'
    if any(isinstance(n, ast.Call) for n in ast.walk(tree)):
        return False, 'calls_not_allowed'
    ns = {'__builtins__': {}}
    try:
        exec(compile(tree, '<perf-sanity>', 'exec'), ns, ns)
        f = ns['clamp']
        for args, exp in [
            ((5, 0, 10), 5), ((-1, 0, 10), 0),
            ((99, 0, 10), 10), ((3, 3, 3), 3),
        ]:
            if f(*args) != exp:
                return False, 'unit_fail:%s' % (args,)
    except Exception as e:
        return False, 'exec:%s:%s' % (type(e).__name__, e)
    return True, 'PASS'

def sanity(phase, model_id):
    specs = [
        ('arithmetic', 'Compute 17*19. Return only the integer.', lambda s: s == '323', 64),
        ('extract', 'Read this exact token: ZEBRA-4821. Return only that token.', lambda s: s == 'ZEBRA-4821', 64),
        ('json', 'Return only valid JSON with exactly these values: alpha is integer 7 and beta is string "blue".', lambda s: json.loads(s) == {'alpha': 7, 'beta': 'blue'}, 64),
        ('italian', 'Nel testo seguente il colore dichiarato è cobalto. Rispondi solo con il nome del colore.', lambda s: s.casefold() == 'cobalto', 64),
        ('english', 'Alice is first and Bob is second. Who is second? Return only the name.', lambda s: s == 'Bob', 64),
    ]
    tests = []
    for name, prompt, check, max_tokens in specs:
        payload = {
            'model': model_id,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.0,
            'seed': 1,
            'max_tokens': max_tokens,
            'stream': False,
            'cache_prompt': False,
        }
        try:
            _, resp = req('/v1/chat/completions', payload, timeout=300)
            choice = resp['choices'][0]
            text = (choice['message'].get('content') or '').strip()
            try:
                ok = bool(check(text))
                reason = 'PASS' if ok else 'expected_mismatch'
            except Exception as e:
                ok = False
                reason = 'check:%s:%s' % (type(e).__name__, e)
            tests.append({
                'name': name, 'pass': ok, 'reason': reason, 'text': text,
                'finish_reason': choice.get('finish_reason'),
            })
        except Exception as e:
            tests.append({
                'name': name, 'pass': False,
                'reason': 'request:%s:%s' % (type(e).__name__, e),
                'text': '', 'finish_reason': None,
            })

    prompt = (
        'Return only Python code defining clamp(x, lo, hi). '
        'It must return lo when x < lo, hi when x > hi, otherwise x. '
        'Do not import anything and do not call other functions.'
    )
    payload = {
        'model': model_id,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.0, 'seed': 1, 'max_tokens': 96,
        'stream': False, 'cache_prompt': False,
    }
    try:
        _, resp = req('/v1/chat/completions', payload, timeout=300)
        choice = resp['choices'][0]
        text = (choice['message'].get('content') or '').strip()
        ok, reason = code_gate(text)
        tests.append({
            'name': 'code_clamp', 'pass': ok, 'reason': reason,
            'text': text, 'finish_reason': choice.get('finish_reason'),
        })
    except Exception as e:
        tests.append({
            'name': 'code_clamp', 'pass': False,
            'reason': 'request:%s:%s' % (type(e).__name__, e),
            'text': '', 'finish_reason': None,
        })

    return {
        'phase': phase,
        'status': 'PASS' if all(x['pass'] for x in tests) else 'FAIL',
        'tests': tests,
        'finished_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    }

def stream_completion(ids, label, measured, server_pid):
    payload = {
        'prompt': ids,
        'n_predict': target_out,
        'temperature': 0.0,
        'seed': 1,
        'top_k': 0,
        'top_p': 1.0,
        'min_p': 0.0,
        'repeat_penalty': 1.0,
        'presence_penalty': 0.0,
        'frequency_penalty': 0.0,
        'dry_multiplier': 0.0,
        'xtc_probability': 0.0,
        'ignore_eos': False,
        'cache_prompt': False,
        'return_tokens': True,
        'stream': True,
        'timings_per_token': True,
        'return_progress': True,
        'sse_ping_interval': -1,
    }
    before = system_snapshot(server_pid)
    t_submit = time.perf_counter()
    measure = StreamMeasure(target_out, t_submit)
    request = urllib.request.Request(
        BASE + '/completion',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    error = None
    try:
        with urllib.request.urlopen(request, timeout=900) as resp:
            for raw in resp:
                now = time.perf_counter()
                line = raw.decode(errors='replace').strip()
                if not line or line.startswith(':') or not line.startswith('data:'):
                    continue
                body = line[5:].strip()
                if not body or body == '[DONE]':
                    continue
                measure.feed(json.loads(body), now)
    except Exception as e:
        error = '%s:%s' % (type(e).__name__, e)
        measure.timeout(time.perf_counter())
    if measure.t_done is None:
        measure.t_done = time.perf_counter()

    result = measure.finalize()
    native = result.get('native_final') or {}
    timings = native.get('timings') or {}
    tokens_cached = native.get('tokens_cached')
    tokens_evaluated = native.get('tokens_evaluated')
    prompt_n = timings.get('prompt_n')
    expected = len(ids)
    progress_cache = [
        int(x.get('cache', 0)) for x in result.get('prompt_progress', [])
        if isinstance(x, dict)
    ]
    native_cache_n = timings.get('cache_n')
    cache_gate = (
        native_cache_n == 0
        and all(x == 0 for x in progress_cache)
        and tokens_evaluated == expected
        and prompt_n == expected
    )
    result.update({
        'label': label,
        'measured': measured,
        'input_tokens_frozen': expected,
        'error': error,
        'cache_prompt': False,
        # tokens_cached in this build reflects resident context length at the
        # end of generation, not prompt-prefix reuse. Keep it as raw evidence
        # but gate reuse from cache_n/progress.cache + full prompt evaluation.
        'tokens_cached_raw': tokens_cached,
        'tokens_evaluated': tokens_evaluated,
        'native_prompt_n': prompt_n,
        'native_cache_n': native_cache_n,
        'prompt_progress_cache': progress_cache,
        'cache_gate_pass': cache_gate,
        'input_count_gate_pass': (
            tokens_evaluated == expected if tokens_evaluated is not None
            else prompt_n == expected
        ),
        'native_prompt_n_gate_pass': (
            prompt_n == expected if prompt_n is not None else None
        ),
        'native_timings': timings,
        'resource_before': before,
        'resource_after': system_snapshot(server_pid),
    })
    result['measurement_eligible'] = (
        result['status'] == 'VALID_128'
        and error is None
        and result['cache_gate_pass']
        and result['input_count_gate_pass']
    )
    return result

atomic_json(RUN / 'load.json', {
    'status': 'IN_PROGRESS',
    'started_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'memory_before': system_snapshot(),
})
atomic_json(RUN / 'quality.json', {'status': 'NOT_EVALUATED'})

cmd = [
    SERVER, '-m', MODEL,
    '--device', 'ROCm0', '--split-mode', 'none',
    '-ngl', 'all', '-c', '4096', '-b', '512', '-ub', '128',
    '-np', '1', '--no-cont-batching', '-fa', 'auto',
    '--host', HOST, '--port', str(PORT), '--reasoning', 'off', '--metrics',
]
log = LOG.open('w')
proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
stopping = False

def stop_server():
    global stopping
    if stopping:
        return
    stopping = True
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)

def on_signal(sig, frame):
    stop_server()
    raise SystemExit(128 + sig)

signal.signal(signal.SIGTERM, on_signal)
signal.signal(signal.SIGINT, on_signal)

start = time.monotonic()
last_err = ''
while time.monotonic() - start < LOAD_TIMEOUT:
    if proc.poll() is not None:
        atomic_json(RUN / 'load.json', {
            'status': 'FAIL', 'cause': 'SERVER_EXIT_%s' % proc.returncode,
            'load_s': time.monotonic() - start,
        })
        raise SystemExit(proc.returncode or 41)
    try:
        code, body = req('/health', timeout=2)
        if code == 200:
            break
    except Exception as e:
        last_err = '%s:%s' % (type(e).__name__, e)
    time.sleep(1)
else:
    atomic_json(RUN / 'load.json', {
        'status': 'FAIL', 'cause': 'HEALTH_TIMEOUT',
        'last_error': last_err, 'load_s': time.monotonic() - start,
    })
    stop_server()
    raise SystemExit(42)

load_s = time.monotonic() - start
try:
    _, models = req('/v1/models', timeout=5)
    model_id = models['data'][0]['id']
except Exception:
    model_id = 'mimo-mixed'

tokenizer_checks = {}
for key in ('512', '2048'):
    w = workloads[key]
    _, out = req('/tokenize', {
        'content': w['rendered_text'],
        'add_special': False,
        'parse_special': True,
    }, timeout=60)
    got = [int(x) for x in out['tokens']]
    expected = w['input_token_ids']
    tokenizer_checks[key] = {
        'match': got == expected,
        'got_count': len(got),
        'expected_count': len(expected),
    }
    if got != expected:
        atomic_json(RUN / 'load.json', {
            'status': 'FAIL', 'cause': 'TOKENIZER_ID_MISMATCH',
            'tokenizer_checks': tokenizer_checks,
        })
        stop_server()
        raise SystemExit(43)

atomic_json(RUN / 'load.json', {
    'status': 'PASS',
    'load_s': load_s,
    'finished_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'pid': proc.pid,
    'model_id': model_id,
    'command': cmd,
    'tokenizer_checks': tokenizer_checks,
    'memory_after_load': system_snapshot(proc.pid),
    'runtime_commit': '58367713a6935c0810103378144008df32e3d5db',
})

pre = sanity('preflight', model_id)
atomic_json(RUN / 'sanity-pre.json', pre)
atomic_json(RUN / 'quality.json', {
    'status': 'IN_PROGRESS' if pre['status'] == 'PASS' else 'FAIL',
    'preflight': pre, 'postflight': None,
})
if pre['status'] != 'PASS':
    stop_server()
    raise SystemExit(44)

warmups = []
for target in doc['warmup_order']:
    result = stream_completion(
        workloads[str(target)]['input_token_ids'],
        'warmup-%s' % target, False, proc.pid,
    )
    result['input_length'] = target
    warmups.append(result)
atomic_json(RUN / 'warmups.json', {'status': 'COMPLETE', 'warmups': warmups})

measured = []
rep = {512: 0, 2048: 0}
for idx, target in enumerate(doc['request_order'], 1):
    rep[target] += 1
    result = stream_completion(
        workloads[str(target)]['input_token_ids'],
        'measure-%02d-%s-r%s' % (idx, target, rep[target]),
        True, proc.pid,
    )
    result.update({
        'request_index': idx,
        'input_length': target,
        'replicate': rep[target],
        'input_token_ids_sha256': workloads[str(target)]['input_token_ids_sha256'],
    })
    measured.append(result)
    append_jsonl(RUN / 'raw-results.jsonl', result)

post = sanity('postflight', model_id)
atomic_json(RUN / 'sanity-post.json', post)
quality_status = 'PASS' if pre['status'] == 'PASS' and post['status'] == 'PASS' else 'FAIL'
atomic_json(RUN / 'quality.json', {
    'status': quality_status,
    'preflight': pre,
    'postflight': post,
})

atomic_json(RUN / 'arm-result.json', {
    'schema': 'mimo26-perf-arm-a-v1',
    'arm': 'A_mixed_single_strix',
    'load': json.loads((RUN / 'load.json').read_text()),
    'sanity_pre': pre,
    'warmups': warmups,
    'measurements': measured,
    'sanity_post': post,
    'quality_status': quality_status,
    'resource_final': system_snapshot(proc.pid),
})
stop_server()
log.close()
raise SystemExit(0 if quality_status == 'PASS' else 45)
