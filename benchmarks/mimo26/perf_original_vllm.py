#!/usr/bin/env python3
from __future__ import annotations
import ast
import json
import os
import time
from pathlib import Path

import torch.distributed as dist
from vllm import LLM, SamplingParams

from perf_measure_common import (
    append_jsonl,
    atomic_json,
    classify_output,
    system_snapshot,
    vllm_metrics_to_dict,
)
from vllm_patch import apply_mimo26_vllm_patches

MODEL = os.environ.get(
    'MIMO26_MODEL',
    '/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL',
)
RUN = Path(os.environ['MIMO26_RUN_DIR'])
WORKLOADS = Path(os.environ['MIMO26_WORKLOADS'])
rank = int(os.environ.get('RANK', '0'))
world = int(os.environ.get('WORLD_SIZE', '1'))
RUN.mkdir(parents=True, exist_ok=True)
doc = json.loads(WORKLOADS.read_text())
workloads = doc['workloads']
target_out = int(doc['sampling']['max_output_tokens'])

apply_mimo26_vllm_patches()

kwargs = dict(
    model=MODEL,
    runner='generate',
    trust_remote_code=True,
    language_model_only=True,
    tensor_parallel_size=2,
    pipeline_parallel_size=1,
    distributed_executor_backend='external_launcher',
    dtype='bfloat16',
    max_model_len=4096,
    max_num_seqs=1,
    max_num_batched_tokens=512,
    kv_cache_memory_bytes=1073741824,
    enforce_eager=True,
    disable_custom_all_reduce=True,
    enable_expert_parallel=False,
    enable_prefix_caching=False,
    seed=1,
    moe_backend='triton_unfused',
    disable_log_stats=False,
)

if rank == 0:
    atomic_json(RUN / 'load.json', {
        'status': 'IN_PROGRESS',
        'started_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'memory_before': system_snapshot(),
    })
    atomic_json(RUN / 'quality.json', {'status': 'NOT_EVALUATED'})

t0 = time.perf_counter()
llm = LLM(**kwargs)
load_s = time.perf_counter() - t0
tok = llm.get_tokenizer()

tokenizer_checks = {}
for key in ('512', '2048'):
    w = workloads[key]
    rendered_ids = tok.encode(w['rendered_text'], add_special_tokens=False)
    templated = tok.apply_chat_template(
        w['messages'],
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    if hasattr(templated, 'keys'):
        templated = templated['input_ids']
    if hasattr(templated, 'tolist'):
        templated = templated.tolist()
    if templated and isinstance(templated[0], list):
        templated = templated[0]
    frozen = w['input_token_ids']
    tokenizer_checks[key] = {
        'rendered_match': list(rendered_ids) == frozen,
        'template_match': [int(x) for x in templated] == frozen,
        'count': len(frozen),
    }
    if not tokenizer_checks[key]['rendered_match'] or not tokenizer_checks[key]['template_match']:
        raise RuntimeError('TOKENIZER_ID_MISMATCH_%s' % key)

if rank == 0:
    atomic_json(RUN / 'load.json', {
        'status': 'PASS',
        'load_s': load_s,
        'finished_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'tp': 2,
        'pp': 1,
        'moe_backend': 'triton_unfused',
        'kv_cache_memory_bytes': 1073741824,
        'tokenizer_checks': tokenizer_checks,
        'memory_after_load': system_snapshot(),
    })

def chat_ids(text):
    ids = tok.apply_chat_template(
        [{'role': 'user', 'content': text}],
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    if hasattr(ids, 'keys'):
        ids = ids['input_ids']
    if hasattr(ids, 'tolist'):
        ids = ids.tolist()
    if ids and isinstance(ids[0], list):
        ids = ids[0]
    return [int(x) for x in ids]

def greedy(ids, max_tokens):
    p = SamplingParams(
        temperature=0.0,
        seed=1,
        max_tokens=max_tokens,
        repetition_penalty=1.0,
        presence_penalty=0.0,
        frequency_penalty=0.0,
        ignore_eos=False,
    )
    out = llm.generate(ids, p, use_tqdm=False)[0]
    c = out.outputs[0]
    return {
        'text': c.text.strip(),
        'token_ids': list(c.token_ids),
        'finish_reason': c.finish_reason,
    }

def code_gate(text):
    code = text.strip()
    fence = chr(96) * 3
    if code.startswith(fence):
        lines = code.splitlines()[1:]
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

def sanity(phase):
    specs = [
        ('arithmetic', 'Compute 17*19. Return only the integer.', lambda s: s == '323', 64),
        ('extract', 'Read this exact token: ZEBRA-4821. Return only that token.', lambda s: s == 'ZEBRA-4821', 64),
        ('json', 'Return only valid JSON with exactly these values: alpha is integer 7 and beta is string "blue".', lambda s: json.loads(s) == {'alpha': 7, 'beta': 'blue'}, 64),
        ('italian', 'Nel testo seguente il colore dichiarato è cobalto. Rispondi solo con il nome del colore.', lambda s: s.casefold() == 'cobalto', 64),
        ('english', 'Alice is first and Bob is second. Who is second? Return only the name.', lambda s: s == 'Bob', 64),
    ]
    tests = []
    for name, prompt, check, n in specs:
        r = greedy(chat_ids(prompt), n)
        try:
            ok = bool(check(r['text']))
            reason = 'PASS' if ok else 'expected_mismatch'
        except Exception as e:
            ok = False
            reason = 'check:%s:%s' % (type(e).__name__, e)
        tests.append({
            'name': name, 'pass': ok, 'reason': reason,
            'text': r['text'], 'finish_reason': r['finish_reason'],
        })

    prompt = (
        'Return only Python code defining clamp(x, lo, hi). '
        'It must return lo when x < lo, hi when x > hi, otherwise x. '
        'Do not import anything and do not call other functions.'
    )
    r = greedy(chat_ids(prompt), 96)
    ok, reason = code_gate(r['text'])
    tests.append({
        'name': 'code_clamp', 'pass': ok, 'reason': reason,
        'text': r['text'], 'finish_reason': r['finish_reason'],
    })
    return {
        'phase': phase,
        'status': 'PASS' if all(x['pass'] for x in tests) else 'FAIL',
        'tests': tests,
        'finished_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    }

def generate_perf(ids, label, measured):
    if dist.is_initialized():
        dist.barrier()
    before = system_snapshot()
    p = SamplingParams(
        temperature=0.0,
        seed=1,
        max_tokens=target_out,
        repetition_penalty=1.0,
        presence_penalty=0.0,
        frequency_penalty=0.0,
        ignore_eos=False,
    )
    t_submit = time.perf_counter()
    out = llm.generate(ids, p, use_tqdm=False)[0]
    t_done = time.perf_counter()
    c = out.outputs[0]
    output_ids = list(c.token_ids)
    metrics = vllm_metrics_to_dict(out.metrics)
    cached = out.num_cached_tokens
    prompt_match = list(out.prompt_token_ids or []) == ids
    latency = t_done - t_submit
    result = {
        'arm': 'B_original_tp2',
        'rank': rank,
        'label': label,
        'measured': measured,
        'input_tokens_frozen': len(ids),
        'prompt_ids_match': prompt_match,
        'num_cached_tokens': cached,
        'cache_gate_pass': cached == 0,
        'output_tokens': len(output_ids),
        'output_token_ids': output_ids,
        'text': c.text,
        'finish_reason': c.finish_reason,
        'status': classify_output(len(output_ids), target_out, c.finish_reason, True),
        't_submit_monotonic': t_submit,
        't_done_monotonic': t_done,
        'ttft_observed_s': None,
        'request_latency_s': latency,
        'end_to_end_output_rate_tps': (
            len(output_ids) / latency if latency > 0 else None
        ),
        'engine_metrics': metrics,
        'prefill_engine_measured': None,
        'resource_before': before,
        'resource_after': system_snapshot(),
    }
    result['measurement_eligible'] = (
        result['status'] == 'VALID_128'
        and result['cache_gate_pass']
        and result['prompt_ids_match']
    )
    if dist.is_initialized():
        dist.barrier()
    return result

pre = sanity('preflight')
if rank == 0:
    atomic_json(RUN / 'sanity-pre.json', pre)
    atomic_json(RUN / 'quality.json', {
        'status': 'IN_PROGRESS' if pre['status'] == 'PASS' else 'FAIL',
        'preflight': pre, 'postflight': None,
    })
if pre['status'] != 'PASS':
    raise SystemExit(40)

warmups = []
for target in doc['warmup_order']:
    r = generate_perf(
        workloads[str(target)]['input_token_ids'],
        'warmup-%s' % target,
        False,
    )
    r['input_length'] = target
    warmups.append(r)
if rank == 0:
    atomic_json(RUN / 'warmups.json', {'status': 'COMPLETE', 'warmups': warmups})

measured = []
rep = {512: 0, 2048: 0}
rank_raw = RUN / ('rank%d-raw-results.jsonl' % rank)
for idx, target in enumerate(doc['request_order'], 1):
    rep[target] += 1
    r = generate_perf(
        workloads[str(target)]['input_token_ids'],
        'measure-%02d-%s-r%s' % (idx, target, rep[target]),
        True,
    )
    r.update({
        'request_index': idx,
        'input_length': target,
        'replicate': rep[target],
        'input_token_ids_sha256': workloads[str(target)]['input_token_ids_sha256'],
    })
    measured.append(r)
    append_jsonl(rank_raw, r)
    if rank == 0:
        append_jsonl(RUN / 'raw-results.jsonl', r)

post = sanity('postflight')
quality_status = 'PASS' if pre['status'] == 'PASS' and post['status'] == 'PASS' else 'FAIL'
if rank == 0:
    atomic_json(RUN / 'sanity-post.json', post)
    atomic_json(RUN / 'quality.json', {
        'status': quality_status,
        'preflight': pre,
        'postflight': post,
    })
    atomic_json(RUN / 'arm-result.json', {
        'schema': 'mimo26-perf-arm-b-v1',
        'arm': 'B_original_tp2',
        'load': json.loads((RUN / 'load.json').read_text()),
        'sanity_pre': pre,
        'warmups': warmups,
        'measurements': measured,
        'sanity_post': post,
        'quality_status': quality_status,
        'resource_final': system_snapshot(),
    })
if dist.is_initialized():
    dist.barrier()
raise SystemExit(0 if quality_status == 'PASS' else 41)
