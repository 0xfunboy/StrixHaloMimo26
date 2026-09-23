#!/usr/bin/env python3
"""CPU-only recovery audit. Never imports a model, calls inference, or changes services.

Read original run files, derive new records, and optionally write audited reports.
All source-run bytes are checked again after writing. Existing reports are archived
once before replacement; original and legacy raw JSONL files are never overwritten.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / 'docs/mimo26/perf-baseline-001'
AUDIT = DOC / 'recovery-audit'
ROOT = Path('/home/funboy/.local/state/strixhalomimo26/windows')
RUNS = {'A': ROOT / 'perf-baseline-001-A-mixed-001',
        'B': ROOT / 'perf-baseline-001-B-original-001'}
ORDER = [512, 2048, 2048, 512, 512, 2048]
COMMON_SHA = 'a580585b901d15ecf70f65adb7c2510f0983a87be21ff81ea2e437ea8839d364'
A_SCRIPT_SHA = '952c5583b5eda447862c9f803b2ecc14de6fc20a84e33bc16d03d6b2176a39c9'
B_SCRIPT_SHA = '7c6b0053ee96d32d3f11ed1d1feebe163c3d7d89adcf502fd2fa5dfbb68e8b97'
PATCH_SHA = 'eeb66fefbf1b63459e5712c031399f2d24d9ac05956c97b4e979ad03b901be72'
WORKLOAD_SHA = '905e3214673560903f60a396546e0e624f9851eccaea8c3cdd369924aecad5c6'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def near(a: float, b: float, message: str) -> None:
    require(math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-9), message)


def stats(values: list[float | int]) -> dict[str, Any]:
    require(bool(values), 'empty metric series')
    return {'n': len(values), 'median': statistics.median(values),
            'min': min(values), 'max': max(values), 'values': values}


def corrected_a(row: dict[str, Any]) -> tuple[list[int], int]:
    """Remove ONLY the proven leading progress placeholders; retain original raw."""
    native = row['native_final']
    timing = native['timings']
    count = native['tokens_predicted']
    progress = row['prompt_progress']
    ids = row['output_token_ids']
    extra = len(ids) - count
    require(count == timing['predicted_n'] == 128, 'A native output count mismatch')
    require(extra > 0 and extra == len(progress), 'A progress/extra count mismatch')
    require(ids[:extra] == [0] * extra, 'A extra IDs are not exactly leading zeros')
    require(len(ids[extra:]) == 128, 'A corrected ID count mismatch')
    require(row['complete'] and row['error'] is None, 'A request incomplete/error')
    require(native['stop'] and row['finish_reason'] == native['stop_type'] == 'limit',
            'A terminal stop mismatch')
    length = row['input_length']
    require(timing['prompt_n'] == native['tokens_evaluated'] == length,
            'A incomplete prompt processing')
    require(timing['cache_n'] == 0 and bool(progress), 'A missing/nonzero native cache')
    require(all(x['cache'] == 0 and x['total'] == length for x in progress),
            'A progress cache mismatch')
    processed = [x['processed'] for x in progress]
    require(processed == sorted(processed) and processed[0] == 0 and processed[-1] == length,
            'A incomplete progress trajectory')
    settings = native['generation_settings']
    for key, expected in {'temperature': 0.0, 'seed': 1, 'ignore_eos': False,
                          'repeat_penalty': 1.0, 'presence_penalty': 0.0,
                          'frequency_penalty': 0.0, 'n_predict': 128,
                          'speculative.types': 'none'}.items():
        require(settings[key] == expected, 'A sampling mismatch: ' + key)
    return ids[extra:], extra


def sanity_check(value: dict[str, Any]) -> dict[str, Any]:
    tests = value['tests']
    names = ['arithmetic', 'extract', 'json', 'italian', 'english', 'code_clamp']
    require([t['name'] for t in tests] == names, 'sanity set changed')
    checks = [tests[0]['text'] == '323', tests[1]['text'] == 'ZEBRA-4821',
              json.loads(tests[2]['text']) == {'alpha': 7, 'beta': 'blue'},
              tests[3]['text'].casefold() == 'cobalto', tests[4]['text'] == 'Bob']
    # Extract only the already-reviewed, frozen validator function. Do not import
    # the executable benchmark module (which loads vLLM at module scope).
    tree = ast.parse((REPO / 'benchmarks/mimo26/perf_original_vllm.py').read_text())
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'code_gate')
    ns: dict[str, Any] = {'ast': ast}
    exec(compile(ast.Module(body=[func], type_ignores=[]), '<frozen-validator-only>', 'exec'), ns)
    ok, reason = ns['code_gate'](tests[5]['text'])
    checks.append(ok)
    require(all(checks), 'persisted sanity output failed unchanged validator: ' + reason)
    require(value['status'] == 'PASS' and all(t['pass'] for t in tests), 'sanity receipt mismatch')
    require(all(t['finish_reason'] == 'stop' for t in tests), 'sanity not natural stop')
    return {'status': 'PASS', 'n': 6, 'finished_at': value['finished_at'],
            'tests': tests, 'audit_method': 'saved outputs revalidated CPU-only; no inference',
            'token_level_trace': 'NOT_PERSISTED_IN_PERFORMANCE_SANITY',
            'adapter': 'A: nonstream chat endpoint; B: offline generate; A SSE client not qualified by this suite'}


def resources(rows: list[dict[str, Any]]) -> dict[str, Any]:
    snapshots = [r[k] for r in rows for k in ['resource_before', 'resource_after']]
    out: dict[str, Any] = {'sampling': 'before/after only, 12 snapshots; not continuous or peaks'}
    for key in ['MemAvailable', 'SwapFree']:
        out[key + '_bytes'] = stats([x['mem'][key] for x in snapshots])
        out[key + '_gib'] = stats([x['mem'][key] / 2**30 for x in snapshots])
    out['process_VmSwap_bytes'] = stats([x['process']['VmSwap'] for x in snapshots])
    out['process_VmSwap_gib'] = stats([x['process']['VmSwap'] / 2**30 for x in snapshots])
    gpu = [x['amd_smi']['gpu_data'][0] for x in snapshots]
    for section, key, name in [('temperature', 'edge', 'gpu_edge_C'),
                               ('temperature', 'apu_temperature_gfx', 'apu_gfx_C'),
                               ('clock', 'apu_average_gfxclk_frequency', 'gfx_clock_MHz'),
                               ('power', 'apu_average_socket_power', 'apu_socket_W')]:
        out[name] = stats([x[section][key]['value'] for x in gpu])
    delta = []
    for r in rows:
        a, b = r['resource_before']['process'], r['resource_after']['process']
        require(a['pid'] == b['pid'], 'resource PID changed within request')
        delta.append({'request': r['label'], 'input': r['input_length'], 'pid': a['pid'],
                      'major_faults': b['majflt'] - a['majflt'],
                      'read_bytes': b['io']['read_bytes'] - a['io']['read_bytes']})
    require(all(x['major_faults'] >= 0 and x['read_bytes'] >= 0 for x in delta), 'negative resource delta')
    out['request_deltas'] = delta
    out['total_major_faults'] = sum(x['major_faults'] for x in delta)
    out['total_read_bytes'] = sum(x['read_bytes'] for x in delta)
    out['throttling'] = 'NOT_OBSERVED_BY_THIS_COLLECTOR'
    out['interpretation'] = 'UMA indicators overlap; no RSS/PSS/MemAvailable/GTT sum; VmSwap is not weight-swap proof.'
    return out


def build() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    require(sha(DOC / 'workloads.json') == WORKLOAD_SHA, 'frozen workload changed')
    require(sha(AUDIT / 'perf_measure_common.frozen.py') == COMMON_SHA, 'recovered common hash mismatch')
    require(sha(REPO / 'benchmarks/mimo26/perf_original_vllm.py') == B_SCRIPT_SHA, 'B frozen script mismatch')
    require(sha(REPO / 'benchmarks/mimo26/vllm_patch.py') == PATCH_SHA, 'patch mismatch')
    workload = load(DOC / 'workloads.json')
    require(workload['request_order'] == ORDER and workload['warmup_order'] == [512, 2048], 'order mismatch')
    for key, w in workload['workloads'].items():
        require(len(w['input_token_ids']) == w['input_tokens'] == int(key), 'workload ID count')
        require(hashlib.sha256(json.dumps(w['input_token_ids'], separators=(',', ':')).encode()).hexdigest()
                == w['input_token_ids_sha256'], 'workload ID hash mismatch')
        require(hashlib.sha256(w['rendered_text'].encode()).hexdigest() == w['rendered_text_sha256'], 'rendered text hash')
    inventory = {str(q): sha(q) for p in RUNS.values() for q in sorted(p.iterdir()) if q.is_file()}
    arms, normalized, raw_rows, native_runs = {}, [], {}, {}
    for arm, p in RUNS.items():
        result = load(p / 'result.json'); whole = load(p / 'arm-result.json')
        measured = lines(p / 'raw-results.jsonl'); warmups = load(p / 'warmups.json')['warmups']
        raw_rows[arm] = measured
        require(measured == whole['measurements'], arm + ' raw/arm disagreement')
        require(warmups == whole['warmups'] and len(warmups) == 2, arm + ' warmup mismatch')
        require([r['input_length'] for r in measured] == ORDER, arm + ' actual order mismatch')
        require([r['input_length'] for r in warmups] == [512, 2048], arm + ' warmup order')
        require([r['request_index'] for r in measured] == list(range(1, 7)), arm + ' request numbering')
        require(Counter(r['input_length'] for r in measured) == {512: 3, 2048: 3}, arm + ' count mismatch')
        require((p / 'launch-count.txt').read_text().strip() == '1', arm + ' multiple launches')
        require(result['run_completion'] == 'PASS' and result['initial_cause'] == 'NORMAL_COMPLETION', arm + ' not terminal success')
        require(result['cleanup']['status'] == 'PASS' and result['cleanup']['k2_state'] == 'READY', arm + ' cleanup fail')
        events = lines(p / 'events.jsonl')
        require(sum(x['event'] == 'RUN_START' for x in events) == 1, arm + ' run replay')
        require(events[-1]['event'] == 'CLEANUP_DONE', arm + ' finalizer incomplete')
        restore = load(p / 'k2-after.json')
        require(restore['state'] == 'READY' and restore['preset'] == 'dspark-k2-gfx1151', arm + ' wrong restore')
        require(restore['paired_backend_http'] == '200' and all(x['health_http'] == '200' for x in restore['ranks']), arm + ' restore health')
        frozen = {}
        for line in (p / 'frozen-SHA256SUMS').read_text().splitlines():
            expected, path = line.split(None, 1); path = path.strip(); frozen[path] = expected
            if Path(path).name not in ['perf_measure_common.py', 'perf_mixed_llama.py']:
                require(sha(Path(path)) == expected, arm + ' frozen mismatch: ' + path)
        checks = whole['load']['tokenizer_checks']
        for key in ['512', '2048']:
            c = checks[key]
            require(c['match'] if arm == 'A' else c['rendered_match'] and c['template_match'], arm + ' runtime tokenizer mismatch')
        pre, post = sanity_check(whole['sanity_pre']), sanity_check(whole['sanity_post'])
        quality = load(p / 'quality.json')
        require(quality['preflight'] == whole['sanity_pre'] == load(p/'sanity-pre.json'), arm+' preflight copy mismatch')
        require(quality['postflight'] == whole['sanity_post'] == load(p/'sanity-post.json'), arm+' postflight copy mismatch')
        native_runs[arm] = {'root': str(p), 'run_id': p.name, 'launches': 1,
                            'started_at': events[0]['iso'], 'restored_at': events[-1]['iso'],
                            'workers': [x for x in events if 'START' in x['event'] and 'RUN_START' != x['event']],
                            'worker_identity_receipts': {q.name: {k:v for k,v in load(q).items() if k in ['Id','InvocationID','MainPID','ActiveState','SubState','Result','ExecMainStatus']} for q in sorted(p.glob('rank*-unit-start.json'))},
                            'cleanup': result['cleanup'], 'restore': restore,
                            'load_s': whole['load']['load_s'], 'sanity_pre': pre, 'sanity_post': post,
                            'tokenizer_checks': checks, 'frozen_sources': frozen}
        for i, r in enumerate(warmups + measured):
            length = r['input_length']; w = workload['workloads'][str(length)]
            measured_flag = i >= 2
            require(r['measured'] == measured_flag, arm + ' phase flag mismatch')
            if measured_flag:
                require(r['input_token_ids_sha256'] == w['input_token_ids_sha256'], arm + ' per-request input hash')
            common = {'arm': arm, 'run_id': p.name, 'request_id': r['label'],
                      'source_file': str(p / ('raw-results.jsonl' if measured_flag else 'warmups.json')),
                      'source_locator': 'line ' + str(i-1) if measured_flag else 'warmups[' + str(i) + ']',
                      'derived_not_original_raw': True, 'measured': measured_flag,
                      'input_tokens': length, 'input_token_ids_sha256': w['input_token_ids_sha256'],
                      'replicate': r.get('replicate'), 'original_status': r['status'],
                      'original_collector_output_tokens': r['output_tokens'],
                      'finish_reason': r['finish_reason'], 'text': r['text'],
                      'ttft_observed_s': None, 'post_first_token_client_rate_tps': None,
                      'request_latency_s': r['request_latency_s'], 'cache_reused_tokens': 0,
                      'input_identity_basis': 'frozen exact IDs + persisted runtime equality checks; not reconstructed tokenization'}
            if arm == 'A':
                ids, extra = corrected_a(r); timing = r['native_final']['timings']
                require(r['native_final']['prompt'] == w['rendered_text'], 'A actual detokenized input mismatch')
                near(r['t_done'] - r['t_submit'], r['request_latency_s'], 'A local latency arithmetic')
                near(127000 / timing['predicted_ms'], timing['predicted_per_second'], 'A native decode arithmetic')
                near(length * 1000 / timing['prompt_ms'], timing['prompt_per_second'], 'A prompt arithmetic')
                common.update(output_tokens=128, output_token_ids=ids, removed_leading_progress_ids=extra,
                              source_original_cache_gate=r['cache_gate_pass'],
                              final_context_tokens_not_reuse=r['native_final']['tokens_cached'],
                              prompt_progress=r['prompt_progress'], t_submit=r['t_submit'], t_done=r['t_done'],
                              local_observer='NODE01 Python HTTP/SSE submit to terminal event',
                              client_metric_gap='first timestamp points to progress placeholder; no true first timestamp saved',
                              native_prompt_ms=timing['prompt_ms'], native_prompt_tps=timing['prompt_per_second'],
                              engine_decode_s=timing['predicted_ms']/1000,
                              engine_decode_tps=timing['predicted_per_second'],
                              engine_decode_observer='llama server synchronized sampling first-to-last; n_gen_steps=n_gen-1',
                              engine_scheduled_to_first_token_s=None,
                              validity='VALID_128_NATIVE_COUNT_WITH_DOCUMENTED_COLLECTOR_CORRECTION')
            else:
                ids = r['output_token_ids']; metric = r['engine_metrics']
                require(len(ids) == r['output_tokens'] == metric['num_generation_tokens'] == 128, 'B output count')
                require(r['prompt_ids_match'] and r['num_cached_tokens'] == 0, 'B input/cache gate')
                require(not metric['is_corrupted'] and r['finish_reason'] == 'length', 'B output corruption/stop')
                near(r['t_done_monotonic']-r['t_submit_monotonic'],r['request_latency_s'],'B local latency arithmetic')
                dt = metric['last_token_ts']-metric['first_token_ts']
                near(127/dt,metric['engine_post_first_token_rate_tps'],'B decode arithmetic')
                common.update(output_tokens=128, output_token_ids=ids,
                              t_submit=r['t_submit_monotonic'], t_done=r['t_done_monotonic'],
                              local_observer='NODE01 Python offline LLM.generate submit to return',
                              client_metric_gap='offline nonstreaming call; no client first-token event',
                              native_prompt_ms=None, native_prompt_tps=None,
                              engine_decode_s=dt, engine_decode_tps=127/dt,
                              engine_decode_observer='vLLM engine-core first/last generated-token event timestamps on rank0',
                              engine_scheduled_to_first_token_s=metric['first_token_ts']-metric['scheduled_ts'],
                              validity='VALID_128')
            common['end_to_end_output_rate_tps'] = 128/common['request_latency_s']
            normalized.append(common)
        cells = {}
        for length in [512, 2048]:
            selected = [r for r in normalized if r['arm']==arm and r['measured'] and r['input_tokens']==length]
            cells[str(length)] = {'n_scheduled': 3, 'n_valid_native_and_local_metrics': len(selected),
                'n_valid_client_ttft': 0, 'output_tokens': [r['output_tokens'] for r in selected],
                'request_ids': [r['request_id'] for r in selected],
                'metrics': {key: (stats([r[key] for r in selected]) if selected[0][key] is not None else None)
                  for key in ['request_latency_s','end_to_end_output_rate_tps','engine_decode_s','engine_decode_tps',
                              'native_prompt_ms','native_prompt_tps','engine_scheduled_to_first_token_s']}}
        arms[arm] = cells
    require(datetime.strptime(native_runs['A']['restored_at'],'%Y-%m-%dT%H:%M:%S%z') <
            datetime.strptime(native_runs['B']['started_at'],'%Y-%m-%dT%H:%M:%S%z'), 'A/B windows overlap')
    peer = lines(DOC / 'B-rank1-raw-results.jsonl')
    require(len(peer)==6, 'peer count')
    for a,b in zip(raw_rows['B'],peer):
        for key in ['label','input_length','input_token_ids_sha256','output_token_ids','text','num_cached_tokens']:
            require(a[key]==b[key], 'rank0/rank1 output/cache identity mismatch '+key)
        require(b['rank']==1, 'peer rank identity')
    live = load(AUDIT/'live-reconciliation.json')
    require(live['peer_rank1_raw']['sha256']==sha(DOC/'B-rank1-raw-results.jsonl'), 'peer receipt hash')
    require(live['controller_status']['epoch']==native_runs['B']['restore']['epoch'], 'live restore epoch changed')
    old = load(ROOT/'mixed-single-correctness-002/load.json')
    before, after = old['memory_before']['MemAvailable'], old['memory_after']['MemAvailable']
    require(before==127883239424 and after==39059042304 and before-after==88824197120, 'principal memory counters')
    confirm = load(ROOT/'mixed-tp1-llama-sanity-001/quality.json')
    prompt = statistics.median(t['response']['timings']['prompt_per_second'] for t in confirm['tests'])
    decode = statistics.median(t['response']['timings']['predicted_per_second'] for t in confirm['tests'])
    near(prompt,57.02004473880432,'diagnostic prompt attribution');near(decode,20.24988356316951,'diagnostic decode attribution')
    confirm_load=load(ROOT/'mixed-tp1-llama-sanity-001/load.json')
    confirm_after=int(confirm_load['memory_after_load']['MemAvailable'].split()[0])*1024
    copied=[]
    for arm,p in RUNS.items():
        for folder in [DOC/'evidence'/arm,DOC/'evidence'/('A-mixed' if arm=='A' else 'B-original')]:
            for q in sorted(folder.iterdir()):
                name={'raw-source.jsonl':'raw-results.jsonl','rank0-raw-source.jsonl':'rank0-raw-results.jsonl'}.get(q.name,q.name)
                target=p/name
                if q.name!='SHA256SUMS' and target.exists():
                    require(sha(q)==sha(target),'evidence copy differs: '+str(q))
                    copied.append({'copy':str(q),'source':str(target),'sha256':sha(q)})
    result = {'schema':'mimo26-perf-baseline-001-recovery-audit-v2','campaign':'PERF-BASELINE-001',
      'audit_mode':'CPU_ONLY_RESULTS_RECOVERY_NO_REPLAY','observed_at':live['observed_at'],
      'gates':{'CORRECTNESS_SANITY':'PASS_BOTH_PRE_POST_OUTPUT_REVALIDATED',
               'PERFORMANCE_MEASUREMENT_COMPLETE':'PARTIAL_12_OF_12_COMPLETIONS_RECOVERED_CLIENT_METRICS_MISSING',
               'METRICS_COMPARABLE':'PARTIAL_ENGINE_DECODE_ONLY', 'CACHE_VERIFIED':'PASS_ALL_12_MEASURED',
               'SOURCE_FREEZE':'PARTIAL_ORIGINAL_A_COLLECTOR_BYTES_NOT_FOUND',
               'QUALITY_RETENTION_VS_ORIGINAL':'NOT_EVALUATED','LONG_CONTEXT':'NOT_EVALUATED',
               'CONCURRENCY':'NOT_EVALUATED','MTP_DFLASH':'NOT_EVALUATED',
               'K2_RESTORE':'PASS_BOTH_HISTORICAL_AND_LIVE'},
      'arms':arms,'run_provenance':native_runs,'workload_sha256':WORKLOAD_SHA,
      'comparison':{str(n):{'engine_decode_rate_ratio_A_over_B':arms['A'][str(n)]['metrics']['engine_decode_tps']['median']/arms['B'][str(n)]['metrics']['engine_decode_tps']['median'],
                          'request_latency_ratio':None,'end_to_end_output_rate_ratio':None,
                          'reason':'HTTP terminal-event and offline generate-return boundaries differ; no common-client normalized ratio.',
                          'ttft_ratio':None,'pure_prefill_ratio':None} for n in [512,2048]},
      'resources':{'A_NODE01':resources(raw_rows['A']),'B_NODE01':resources(raw_rows['B']),'B_NODE02':resources(peer)},
      'source_recovery':{'common_sha256':COMMON_SHA,'common_recovered_from':'02-EVO-X3:/home/funboy/perf_measure_common.py',
          'A_original_expected_sha256':A_SCRIPT_SHA,'A_original_source':'NOT_FOUND',
          'A_search_scope':'actual project scripts, run/evidence roots, first tracked Git version, bounded NODE01 /tmp and home names; no byte-identical copy found',
          'source_reconstruction':'NOT_ATTEMPTED','B_original_sha256':B_SCRIPT_SHA,'patch_sha256':PATCH_SHA},
      'errata':{'principal_memory':{'source':str(ROOT/'mixed-single-correctness-002/load.json'),
          'finished_at':old['finished_at'],'before_bytes':before,'after_bytes':after,'delta_bytes':before-after,
          'before_gib':before/2**30,'after_gib':after/2**30,'delta_gib':(before-after)/2**30},
          'confirmation':{'run':'mixed-tp1-llama-sanity-001','runtime_commit':'97845c4f1ffae096d22ad772df396550f9f78306',
          'prompt_tps':prompt,'decode_tps':decode,'after_bytes':confirm_after,'after_gib':confirm_after/2**30,
          'before_119_33901977539062_gib_provenance':'UNRESOLVED_NO_RAW_RECEIPT_FOUND',
          'delta_82_78940963745117_gib_provenance':'UNRESOLVED_NO_RAW_RECEIPT_FOUND'},
          'principal_performance_before_campaign':'NOT_MEASURED',
          'SSE_cause':'progress chunks ARE tagged prompt_progress; recovered collector appended progress but fell through and counted tokens; tokens_cached is final slot context, not reused prefill.',
          'legacy_raw_results':'root raw-results.jsonl retained as previous derivative; not current canonical dataset'},
      'live_reconciliation':live,'verified_copies':copied,'source_inventory':inventory,
      'limits':['A true first-token timestamp unavailable; do not derive it from native timings.',
                'B client TTFT absent for offline generate; engine scheduled-to-first is not pure prefill.',
                'A natural sanity used nonstream chat, not the defective SSE collector; no full token traces retained for performance sanity.',
                'Original A collector source bytes missing; current edited collector is not substituted as frozen source.',
                'Resource snapshots do not prove absence of all concurrent work or thermal throttling; no new telemetry fabricated.',
                'Before/delta GiB values in the historical confirmation attribution lack supporting raw receipts.',
                'Native decode comparison is engine first-to-last throughput, not client ITL or pure GPU kernel performance.'],
      'next_experiment_proposed_not_executed':'Valutazione separata della qualità su compiti realistici, usando l’originale come riferimento e preregistrando validator e sorgenti completi prima di qualunque futura esecuzione.'}
    return result, normalized, inventory


def format_stat(s: dict[str, Any] | None, decimals: int=3) -> str:
    if s is None:return 'N/A'
    return f"{s['median']:.{decimals}f} [{s['min']:.{decimals}f}–{s['max']:.{decimals}f}]"


def report(d: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    out=['# StrixHaloMimo26 — PERF-BASELINE-001: audit dei risultati recuperati','',
         '**Conclusione: recupero completato; qualifica delle metriche PARZIALE.** Nessun modello è stato avviato e nessuna replica è stata ripetuta.',
         '',f"Verifica live: {d['observed_at']}. Markdown e summary.json derivano dallo stesso insieme di 12 misure e 4 warmup, conservati separatamente.",'',
         '## Configurazioni e provenienza','',
         '- A: Baekpica MQ-IQ2-XXS-XS-Q8-MM-BF16, revision b3794b22b6276f8120c340f52639f5eaa354a3fd; llama.cpp 58367713a6935c0810103378144008df32e3d5db; NODE01 HIP/gfx1151.',
         '- B: Xiaomi MiMo-V2.6-Flash-RL, revision 5711b268169967567844e1e560e8a3966da959b1; vLLM 0.1.0rc2.dev9+g9255fd9fb9.rocm100; Torch 2.13.0+rocm10.0.0; NODE01+NODE02 TP2/PP1, eager, triton_unfused, KV 1 GiB/rank.',
         '- Entrambi: context 4096, una sequenza, thinking/prefix reuse/MTP/DFlash OFF. Output naturale con cap 128, ignore_eos=false. A: batch 512 / ubatch 128, slot 1, GPU layers all, split none. Configurazioni effettive nei config.json dei run.',
         '- I pin pesi sono quelli documentati nel mandato e nei percorsi/manifest esistenti; nessun nuovo hashing massivo o download. Binario A, patch e sorgente B sono stati confrontati con i relativi hash.',
         '',f"Workload SHA256: `{d['workload_sha256']}`. Le liste congelate contengono esattamente 512/2048 ID; i controlli runtime salvati attestano corrispondenza. Ordine comune: 512, 2048, 2048, 512, 512, 2048; warmup 512/2048 esclusi.",'',
         'Il manifest delle 05:34 è posteriore ai run e NON è una preregistrazione. Config e frozen-SHA256SUMS delle finestre sono distinti dagli indici ricostruiti oggi. Il collector comune originale è stato recuperato dal peer con hash esatto; manca ancora la copia byte-identica dello script A, hash atteso `'+A_SCRIPT_SHA+'`. Non è stata ricostruita per ipotesi.','',
         '## Risultati — mediana [min–max], tre repliche per cella','',
         '| Input→output | Braccio | n valido locale/native | Latenza osservatore locale (s) | Output/lat. locale (tok/s) | Decode engine dopo primo token (tok/s) |',
         '|---|---|---:|---:|---:|---:|']
    for length in [512,2048]:
        for arm in ['A','B']:
            c=d['arms'][arm][str(length)];m=c['metrics']
            out.append(f"| {length}→128 | {arm} | {c['n_valid_native_and_local_metrics']} | {format_stat(m['request_latency_s'])} | {format_stat(m['end_to_end_output_rate_tps'])} | {format_stat(m['engine_decode_tps'])} |")
    out += ['', '**Confini distinti:** A cronometra HTTP/SSE fino all’evento terminale; B la chiamata offline LLM.generate fino al ritorno. Le latenze rimangono colonne etichettate per osservatore; i precedenti rapporti 3.87×/2.20× non sono promossi a confronto normalizzato fra client equivalenti.', '',
            'Il decode engine usa `(128−1)/(ultimo−primo token)` all’interno di ciascun motore. La semantica llama è verificata nel sorgente pinned (n_gen_steps=n_gen−1; clock dopo sampling sincronizzato); quella B nei timestamp engine-core. Non sono ITL client né tempi puri dei kernel.']
    for length in [512,2048]:
        out.append(f"- {length}: rapporto decode engine A/B **{d['comparison'][str(length)]['engine_decode_rate_ratio_A_over_B']:.3f}×**.")
    out += ['', '## Prefill e TTFT: non equivalenti','', '| Input | Prompt nativo A, ms | Prompt nativo A, tok/s | B scheduled→first, s | TTFT client A/B |', '|---:|---:|---:|---:|---|']
    for length in [512,2048]:
        a=d['arms']['A'][str(length)]['metrics'];b=d['arms']['B'][str(length)]['metrics']
        out.append(f"| {length} | {format_stat(a['native_prompt_ms'])} | {format_stat(a['native_prompt_tps'])} | {format_stat(b['engine_scheduled_to_first_token_s'])} | N/A / N/A |")
    out += ['', 'Il prompt time nativo A include il campionamento del primo token; non è il solo tempo dei kernel di prefill. Prompt time A e scheduled→first B non sono la stessa metrica; nessun rapporto prefill, nessun N_input/TTFT usato come prefill puro. Primo timestamp A contaminato dai progress event; B non aveva streaming client. n valido TTFT client=0.','',
            '## Tutte le richieste misurate','', '| Braccio / request ID | Input | Output modello | ID grezzi collector | Cache riusata | Latenza s | Decode engine tok/s |', '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        if r['measured']:
            out.append(f"| {r['arm']} / {r['request_id']} | {r['input_tokens']} | {r['output_tokens']} | {r['original_collector_output_tokens']} | 0 | {r['request_latency_s']:.6f} | {r['engine_decode_tps']:.6f} |")
    out += ['', 'Tutte le 12 completion sono conservate. A termina `limit`, B `length`, sempre 128 token reali. Nei raw A rimangono OVER_OUTPUT/cache_gate=false originali: il collector contava 4/7 zeri di progresso e interpretava male il contesto finale. Il derivato rimuove solo quel prefisso provato, verificando conteggi nativi, progress e prompt completo. Non sostituisce timestamp mancanti. I warmup hanno ID distinti e non entrano nelle statistiche.','',
            '## Memoria e risorse per nodo','', '| Braccio/nodo | MemAvailable GiB mediana [min–max] | VmSwap processo GiB | Major fault totali | Read bytes totali |', '|---|---:|---:|---:|---:|']
    for name,r in d['resources'].items():
        out.append(f"| {name} | {format_stat(r['MemAvailable_gib'])} | {format_stat(r['process_VmSwap_gib'])} | {r['total_major_faults']} | {r['total_read_bytes']} |")
    out += ['', '| Braccio/nodo | APU gfx °C | Gfx MHz | APU socket W |', '|---|---:|---:|---:|']
    for name,r in d['resources'].items():
        out.append(f"| {name} | {format_stat(r['apu_gfx_C'],2)} | {format_stat(r['gfx_clock_MHz'],0)} | {format_stat(r['apu_socket_W'],2)} |")
    out += ['', 'Sono 12 snapshot prima/dopo per nodo, non picchi o monitoraggio continuo. VmSwap B non è zero; piccole letture/fault sono conservate. Non si deduce che i pesi fossero su swap né l’assenza di qualunque collo di bottiglia. MemAvailable/RSS/PSS/GTT in UMA non si sommano. Throttling e assenza globale di altri workload durante la finestra non sono provati da questi soli snapshot.','',
            '## Sanity, serializzazione e restore','']
    for arm,r in d['run_provenance'].items():
        out.append(f"- {arm}: `{r['run_id']}`, start {r['started_at']}; restore {r['restored_at']}; un caricamento ({r['load_s']:.3f} s); sanity pre 6/6 e post 6/6, output salvati rivalidati CPU-only; cleanup PASS, K2 READY.")
    out += ['', 'La fine del restore A precede l’inizio B. Le ricevute ripristinano K2 `dspark-k2-gfx1151`, release 5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513, non E1 storico. Il live riconciliato conserva l’epoch finale B 1790127186526215806; rank0/rank1/paired HTTP 200. Nessun processo MiMo riconosciuto dalla scansione e nessun lock pertinente risultano presenti. Le vecchie unità failed sono state preservate, non azzerate.', '',
            'Il sanity A usava chat nonstreaming, non l’adapter SSE difettoso; questa qualifica riguarda i sei output naturali salvati, non una nuova validazione end-to-end del client streaming. I token ID completi del sanity performance non furono persistiti.','',
            '## Errata verificati e limiti residui','',
            'MemAvailable principale: 127883239424→39059042304 byte, delta 88824197120; 119.10054779052734→36.37656784057617 GiB, delta 82.72397994995117 GiB. Il valore 36.54961013793945 GiB appartiene al dopo-load della conferma (38325044 kB). Non è stata trovata la ricevuta per 119.33901977539062 GiB prima e 82.78940963745117 GiB delta: la precedente attribuzione certa alla stessa conferma è ritirata.', '',
            'Le mediane 57.02004473880432 prompt / 20.24988356316951 decode appartengono esclusivamente alla conferma mixed-tp1-llama-sanity-001, build 97845c4f1. Non sono usate nella campagna attuale. Il report di correttezza originario resta preservato.', '',
            '## Gate finali','']
    out.extend(f"- `{k} = {v}`" for k,v in d['gates'].items())
    out += ['', '## Artefatti e riproduzione CPU-only','',
            '- Canonici: `REPORT.md`, `summary.json`, `recovery-audit/normalized-results.jsonl`, `recovery-audit/audit.json`.',
            '- Fonti originali: i due run sotto `/home/funboy/.local/state/strixhalomimo26/windows/`, con hash in `recovery-audit/source-SHA256SUMS` e copie preesistenti verificate.',
            '- `raw-results.jsonl`, `arm-A-corrected.jsonl` e gli altri vecchi derivati rimangono intatti, come evidenza storica; non sono più la fonte del riepilogo corrente.',
            '- Versioni precedenti dei report in `recovery-audit/prior-reports/`; collector comune recuperato in `recovery-audit/perf_measure_common.frozen.py`; stato live in `recovery-audit/live-reconciliation.json`.',
            '- Verifica senza scrittura/inferenza: `python3 scripts/mimo26/audit_perf_baseline_001.py --check`.', '',
            '## Un solo esperimento successivo proposto, non eseguito','',d['next_experiment_proposed_not_executed'],'',
            'Questo è un confronto delle configurazioni complete. Non isola la quantizzazione, i kernel, il numero di nodi o la comunicazione TP2; non prova qualità equivalente IQ2, long context, concorrenza o prontezza produzione.','']
    return '\n'.join(out)


def archive(path: Path) -> None:
    dst=AUDIT/'prior-reports'/path.name
    if path.exists() and not dst.exists():
        dst.parent.mkdir(parents=True,exist_ok=True)
        with dst.open('xb') as f:f.write(path.read_bytes())


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true');parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    require(not(args.write and args.check),'choose --write or --check')
    result,rows,inventory=build()
    encoded=''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in rows)
    text=report(result,rows)
    if args.write:
        AUDIT.mkdir(exist_ok=True)
        for name in ['REPORT.md','summary.json','PERF_BASELINE_001_REPORT.md','PERF_BASELINE_001_REPORT.json',
                     'execution-manifest.json','ERRATUM_CORRECTNESS_REPORT.md','correctness-erratum.json','arm-A-SSE-correction.json']:
            archive(DOC/name)
        (AUDIT/'normalized-results.jsonl').write_text(encoded)
        payload=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
        (DOC/'summary.json').write_text(payload);(AUDIT/'audit.json').write_text(payload)
        (DOC/'REPORT.md').write_text(text)
        (AUDIT/'source-SHA256SUMS').write_text(''.join(f'{h}  {p}\n' for p,h in inventory.items()))
    if args.check:
        require((AUDIT/'normalized-results.jsonl').read_text()==encoded,'normalized dataset not reproducible')
        require(load(DOC/'summary.json')==result==load(AUDIT/'audit.json'),'JSON reports not reproducible/coherent')
        require((DOC/'REPORT.md').read_text()==text,'Markdown not reproducible/coherent')
    require(all(sha(Path(p))==h for p,h in inventory.items()),'original raw changed during audit')
    print(json.dumps({'status':'AUDIT_CHECK_PASS' if args.check else 'AUDIT_WRITE_PASS' if args.write else 'AUDIT_DRY_RUN_PASS',
                      'measurements':sum(r['measured'] for r in rows),'warmups':sum(not r['measured'] for r in rows),
                      'source_files_unchanged':len(inventory),'gates':result['gates'],
                      'comparison':result['comparison']},indent=2))

if __name__=='__main__':main()
