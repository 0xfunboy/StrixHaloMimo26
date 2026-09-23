"""Recompute independent paired quality verdicts CPU-only, with no inference imports."""
from __future__ import annotations
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
from common import atomic,completion_state,digest,ids_sha,read_jsonl,sha,verify_freeze
from validate import same,sanity_verdict,verdict

FAIL={'FAIL_SEMANTIC','FAIL_FORMAT','FAIL_CODE_TEST'}
EVALUABLE={'PASS'}|FAIL


def paired_state(a,b):
    if a not in EVALUABLE or b not in EVALUABLE:return 'OTHER_STATES'
    if a=='PASS' and b=='PASS':return 'BOTH_PASS'
    if a in FAIL and b=='PASS':return 'A_FAIL_B_PASS'
    if a=='PASS' and b in FAIL:return 'A_PASS_B_FAIL'
    return 'BOTH_FAIL'


def check_record(rec,case,arm,index_sha,run,phase):
    errors=[]
    def require(cond,why):
        if not cond:errors.append(why)
    require(rec.get('record_sha256')==digest({k:v for k,v in rec.items() if k!='record_sha256'}),'record digest')
    require(rec.get('campaign')=='QUALITY-RETENTION-001' and rec.get('arm')==arm,'campaign/arm')
    require(rec.get('run_id')==run.name and rec.get('phase')==phase and rec.get('case_id')==case['case_id'],'run/phase/case')
    require(rec.get('source_index_sha256')==index_sha,'source freeze identity')
    require(same(rec.get('input_ids_provided'),case['input_token_ids']),'input ID list')
    require(rec.get('input_ids_sha256')==ids_sha(case['input_token_ids']),'input ID digest')
    require(rec.get('rendered_text')==case['rendered_text'] and rec.get('messages')==case['messages'],'prompt identity')
    require(rec.get('output_cap')==case['output_cap'],'cap changed')
    sampling=rec.get('sampling',{})
    require(sampling.get('temperature')==0 and sampling.get('seed')==1 and sampling.get('ignore_eos') is False and sampling.get('thinking') is False,'sampling changed')
    path=run/'requests'/(phase+'__'+case['case_id'])/'result.json'
    require(path.exists(),'atomic request result missing')
    if path.exists():require(json.loads(path.read_text())==rec,'append index differs from atomic record')
    status=rec.get('completion_status')
    if status in ('TECHNICAL_ERROR','TIMEOUT'):return errors
    raw=rec.get('native_response')
    require(isinstance(raw,dict),'native response missing')
    if not isinstance(raw,dict):return errors
    output_ids=rec.get('output_token_ids');n=rec.get('output_tokens')
    require(isinstance(output_ids,list) and type(n) is int and len(output_ids)==n,'native output ID count')
    require(rec.get('cache_reused_tokens')==0 and rec.get('cache_gate_pass') is True,'cache reuse gate')
    require(rec.get('native_prompt_processed')==len(case['input_token_ids']),'processed prompt count')
    require(rec.get('collector_consistency_pass') is True,'collector consistency')
    require(status==completion_state(rec.get('finish_reason'),n,case['output_cap']),'completion classification')
    require(rec.get('diagnostic_wall_s',float('inf'))<=case['timeout_s'],'deadline exceeded')
    if arm=='A':
        timings=raw.get('timings',{})
        require(raw.get('stop') is True and raw.get('content')==rec.get('final_text'),'A native terminal/content')
        require(raw.get('tokens')==output_ids and raw.get('tokens_predicted')==n and timings.get('predicted_n')==n,'A native output counters')
        require(timings.get('cache_n')==0 and timings.get('prompt_n')==len(case['input_token_ids']) and raw.get('tokens_evaluated')==len(case['input_token_ids']),'A native prompt/cache counters')
        require(raw.get('stop_type')==rec.get('finish_reason'),'A finish reason')
    else:
        outs=raw.get('outputs',[])
        require(raw.get('finished') is True,'B native finished')
        require(raw.get('prompt_token_ids')==case['input_token_ids'] and rec.get('native_input_ids_echoed')==case['input_token_ids'],'B native input echo')
        require(raw.get('num_cached_tokens')==0,'B native cache counter')
        require((raw.get('metrics') or {}).get('is_corrupted',False) is False,'B engine corruption flag')
        require(len(outs)==1,'B native output cardinality')
        if len(outs)==1:
            require(outs[0].get('token_ids')==output_ids and outs[0].get('text')==rec.get('final_text'),'B native content/IDs')
            require(outs[0].get('finish_reason')==rec.get('finish_reason'),'B finish reason')
    return errors


def load_arm(root,manifest,arm,cases,sanity):
    run=Path(manifest['runs'][arm]['run_dir']);index_sha=sha(root/'source-SHA256SUMS')
    p=run/'raw-results.jsonl';records=read_jsonl(p) if p.exists() else []
    inventory={};issues=[];counts=collections.Counter()
    for rec in records:
        key=(rec.get('phase'),rec.get('case_id'));counts[key]+=1
        inventory[key]=rec
    duplicates=[list(k) for k,n in counts.items() if n!=1]
    if duplicates:issues.append({'duplicate_request_keys':duplicates})
    allowed={('panel',c['case_id']) for c in cases}|{(phase,c['case_id']) for phase in ('preflight','postflight') for c in sanity}
    unexpected=[list(k) for k in inventory if k not in allowed]
    if unexpected:issues.append({'unexpected_requests':unexpected})
    full_order=[(phase,c['case_id']) for phase,items in [('preflight',sanity),('panel',cases),('postflight',sanity)] for c in items]
    actual_order=[(r.get('phase'),r.get('case_id')) for r in records]
    if actual_order!=full_order[:len(actual_order)]:issues.append({'request_order':'not expected frozen prefix'})
    config=run/'config.json'
    if not config.exists() or sha(config)!=sha(root/manifest['runs'][arm]['config']):issues.append({'config':'missing or changed'})
    input_checks=json.loads((run/'input-checks.json').read_text()) if (run/'input-checks.json').exists() else {}
    for c in cases+sanity:
        check=input_checks.get(c['case_id'],{})
        if check.get('actual_token_ids')!=c['input_token_ids']:
            issues.append({'runtime_tokenizer_check':c['case_id'],'reason':'not persisted or different'})
    results={};sanity_reports={}
    for phase,items in [('preflight',sanity),('panel',cases),('postflight',sanity)]:
        values=[]
        for case in items:
            rec=inventory.get((phase,case['case_id']))
            if rec is None:
                result={'status':'NOT_RUN','critical_violations':[],'reason':'No atomic request completion recovered'}
            else:
                errors=check_record(rec,case,arm,index_sha,run,phase)
                if counts[(phase,case['case_id'])]!=1:errors.append('duplicate completion record')
                if errors:
                    result={'status':'TECHNICAL_ERROR','critical_violations':[],'reason':'record integrity/contract','errors':errors}
                elif phase!='panel':result=sanity_verdict(case['name'],rec['final_text'],rec['completion_status'])
                else:result={'status':'PENDING_INDEPENDENT_VALIDATION'}
                result.update(request_id=rec['request_id'],record_sha256=rec['record_sha256'],
                    output_tokens=rec['output_tokens'],finish_reason=rec['finish_reason'],completion_status=rec['completion_status'],
                    raw_path=str(run/'requests'/(phase+'__'+case['case_id'])/'result.json'))
            if phase=='panel':results[case['case_id']]={'record':rec,'verdict':result}
            else:values.append({'case_id':case['case_id'],**result})
        if phase!='panel':sanity_reports[phase]={'status':'PASS' if len(values)==6 and all(v['status']=='PASS' for v in values) else 'FAIL_OR_MISSING','cases':values}
    terminal=json.loads((run/'result.json').read_text()) if (run/'result.json').exists() else {}
    restore=json.loads((run/'k2-after.json').read_text()) if (run/'k2-after.json').exists() else {}
    restore_pass=(terminal.get('cleanup',{}).get('status')=='PASS' and restore.get('state')=='READY'
        and restore.get('release_id')==manifest['restore']['release_id'] and restore.get('preset')==manifest['restore']['preset']
        and restore.get('owner')=='DS41' and restore.get('owner_state')=='RUNNING'
        and restore.get('paired_backend_http')=='200' and len(restore.get('ranks',[]))==2
        and all(r.get('active') is True and r.get('health_http')=='200' for r in restore['ranks']))
    meta={'run_id':run.name,'raw_path':str(p),'raw_sha256':sha(p) if p.exists() else None,'raw_records':len(records),
        'issues':issues,'sanity':sanity_reports,'run_completion':terminal.get('run_completion','NOT_STARTED'),
        'initial_cause':terminal.get('initial_cause'),'cleanup':terminal.get('cleanup'),
        'restore_receipt':restore,'restore_pass':restore_pass,'launch_count':int((run/'launch-count.txt').read_text()) if (run/'launch-count.txt').exists() else 0,
        'load':json.loads((run/'load.json').read_text()) if (run/'load.json').exists() else None}
    return results,meta,records


def evaluate(root):
    frozen=verify_freeze(root)
    manifest=json.loads((root/'source-manifest.json').read_text())
    prep=json.loads((root/'preparation.json').read_text())
    assert prep['source_index_sha256']==frozen['index_sha256'],'PREPARATION_INDEX_MISMATCH'
    cases=read_jsonl(root/'cases.jsonl');sanity=read_jsonl(root/'sanity.jsonl');expected={x['case_id']:x for x in read_jsonl(root/'expected.jsonl')}
    assert len(cases)==24 and list(expected)==[c['case_id'] for c in cases]
    results={};arms={};raw=[]
    for arm in ('A','B'):
        results[arm],arms[arm],records=load_arm(root,manifest,arm,cases,sanity)
        for r in records:
            raw.append({'aggregate_role':'DERIVED_INDEX_ORIGINAL_RECORD_UNCHANGED','source_file':arms[arm]['raw_path'],'source_sha256':arms[arm]['raw_sha256'],'record':r})
    # NODE02 original records are independently copied only after the distributed window is terminal.
    peer_path=root/'evidence/B-rank1-raw-results.jsonl'
    peer_validation={'status':'MISSING','record_count':0}
    if peer_path.exists():
        peer=read_jsonl(peer_path)
        primary={ (x['record']['phase'],x['record']['case_id']):x['record'] for x in raw if x['record']['arm']=='B'}
        ok=len(peer)==36 and len(primary)==36
        for rec in peer:
            other=primary.get((rec.get('phase'),rec.get('case_id')))
            ok=ok and rec.get('record_sha256')==digest({k:v for k,v in rec.items() if k!='record_sha256'})
            ok=ok and other is not None and all(same(rec.get(k),other.get(k)) for k in ('input_ids_provided','output_token_ids','output_tokens','final_text','finish_reason','completion_status','source_index_sha256'))
            ok=ok and rec.get('rank')==1 and rec.get('arm')=='B'
        receipt_path=root/'evidence/peer-copy-receipt.json'
        receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
        ok=ok and receipt.get('sha256')==sha(peer_path) and receipt.get('node')=='02-EVO-X3'
        peer_validation={'status':'PASS' if ok else 'FAIL','record_count':len(peer),'sha256':sha(peer_path),'receipt':receipt}
    arms['B']['peer_crosscheck']=peer_validation
    pairs=[]
    for c in cases:
        row={'case_id':c['case_id'],'family':c['family'],'language':c['language'],'input_tokens':c['input_tokens'],
             'output_cap':c['output_cap'],'oracle_sha256':digest(expected[c['case_id']])}
        for arm in ('A','B'):
            item=results[arm][c['case_id']];v=item['verdict']
            if v['status']=='PENDING_INDEPENDENT_VALIDATION':
                evaluated=verdict(item['record']['final_text'],expected[c['case_id']],item['record']['completion_status'])
                v={**v,**evaluated}
            row[arm]=v
        row['pair_state']=paired_state(row['A']['status'],row['B']['status'])
        row['critical_regression']=bool(row['A'].get('critical_violations')) and row['B']['status']=='PASS'
        row['input_ids_equal']=(results['A'][c['case_id']]['record'] is not None and results['B'][c['case_id']]['record'] is not None
            and same(results['A'][c['case_id']]['record']['input_ids_provided'],c['input_token_ids'])
            and same(results['B'][c['case_id']]['record']['input_ids_provided'],c['input_token_ids'])
            and same(results['B'][c['case_id']]['record'].get('native_input_ids_echoed'),c['input_token_ids']))
        pairs.append(row)
    counters={arm:dict(collections.Counter(p[arm]['status'] for p in pairs)) for arm in ('A','B')}
    paired_counts=dict(collections.Counter(p['pair_state'] for p in pairs))
    families={}
    for family in dict.fromkeys(c['family'] for c in cases):
        subset=[p for p in pairs if p['family']==family]
        families[family]={'planned':len(subset),'A':dict(collections.Counter(p['A']['status'] for p in subset)),
                         'B':dict(collections.Counter(p['B']['status'] for p in subset)),
                         'paired':dict(collections.Counter(p['pair_state'] for p in subset))}
    regressions=[p['case_id'] for p in pairs if p['pair_state']=='A_FAIL_B_PASS']
    critical_regressions=[p['case_id'] for p in pairs if p['critical_regression']]
    violations={arm:[{'case_id':p['case_id'],'violations':p[arm]['critical_violations']} for p in pairs if p[arm].get('critical_violations')] for arm in ('A','B')}
    live=json.loads((root/'final-live.json').read_text()) if (root/'final-live.json').exists() else {'status':'NOT_CAPTURED'}
    good_sanity=all(arms[a]['sanity'][p]['status']=='PASS' for a in ('A','B') for p in ('preflight','postflight'))
    input_pass=all(p['input_ids_equal'] for p in pairs) and not any(arms[a]['issues'] for a in ('A','B')) and peer_validation['status']=='PASS'
    technical=sum(counters[a].get(s,0) for a in ('A','B') for s in ('TIMEOUT','TECHNICAL_ERROR','NOT_RUN'))
    incomplete=sum(counters[a].get('INCOMPLETE_OUTPUT_CAP',0) for a in ('A','B'))
    review=sum(counters[a].get(s,0) for a in ('A','B') for s in ('VALIDATOR_BLOCKED','NEEDS_REVIEW','CASE_INVALID'))
    complete=(good_sanity and input_pass and technical==0 and all(arms[a]['raw_records']==36 and arms[a]['launch_count']==1 and arms[a]['run_completion']=='PASS' and arms[a]['restore_pass'] for a in ('A','B')))
    gates={'EXPERIMENT_COMPLETION':'COMPLETE' if complete else 'PARTIAL_OR_BLOCKED',
        'SOURCE_FREEZE':frozen['status'],'INPUT_COMPARABILITY':'PASS' if input_pass else 'PARTIAL_OR_FAIL',
        'SANITY_PREFLIGHT':{a:arms[a]['sanity']['preflight']['status'] for a in ('A','B')},
        'SANITY_POSTFLIGHT':{a:arms[a]['sanity']['postflight']['status'] for a in ('A','B')},
        'QUALITY_PANEL_A':counters['A'],'QUALITY_PANEL_B':counters['B'],
        'PAIRED_REGRESSIONS':len(regressions),'CRITICAL_REGRESSIONS':len(critical_regressions),
        'INCOMPLETE_CASES':incomplete,'TECHNICAL_ERRORS':technical,'REVIEW_REQUIRED':review,
        'GENERAL_QUALITY_EQUIVALENCE':'NOT_ESTABLISHED','QUANTIZATION_ONLY_EFFECT':'NOT_ISOLATED',
        'LONG_CONTEXT':'NOT_EVALUATED','CONCURRENCY':'NOT_EVALUATED','MTP_DFLASH':'NOT_EVALUATED',
        'PRODUCTION_PROMOTION':'NOT_PERFORMED',
        'RESTORE_STATUS':{'A':'PASS' if arms['A']['restore_pass'] else 'FAIL_OR_MISSING','B':'PASS' if arms['B']['restore_pass'] else 'FAIL_OR_MISSING','final_live':live.get('status','NOT_CAPTURED')}}
    summary={'schema':'mimo26-quality-paired-summary-v1','campaign':'QUALITY-RETENTION-001',
        'source_freeze':frozen,'preregistration':{'frozen_at':manifest['frozen_at'],'case_order':manifest['case_order'],'cap_per_arm':manifest['output_cap_total_per_arm']},
        'planned_cases_per_arm':24,'planned_completions':48,'evaluable_pairs':sum(p['pair_state']!='OTHER_STATES' for p in pairs),
        'pair_counts':paired_counts,'per_family':families,'regressions':regressions,'critical_regressions':critical_regressions,
        'critical_violations_by_arm':violations,'arms':arms,'gates':gates,'pairs':pairs,'final_live':live,
        'interpretation_limits':['Independent expected values/tests, not agreement with original B.','Exploratory synthetic local panel, not general quality retention or statistical non-inferiority.',
          'Runtime and distribution differ as well as weights; no isolated quantization claim.','Incidental elapsed times are diagnostics, not a new performance benchmark.',
          'All 24 cases remain in the denominator, including incomplete, technical and unreviewable states.']}
    return summary,raw


def render(summary):
    s=summary;g=s['gates'];lines=['# StrixHaloMimo26 — QUALITY-RETENTION-001','',
        '**Stato esperimento:** `'+g['EXPERIMENT_COMPLETION']+'`. Valutazione indipendente appaiata sul pannello sintetico preregistrato.',
        '', 'A = mixed Baekpica, singolo Strix, llama.cpp HIP pinned. B = originale Xiaomi FP8/MXFP4, due Strix, vLLM TP2 pinned; non un oracolo infallibile.',
        '', '## Esiti sul pannello','',
        '| Voce | Risultato |','|---|---|',
        '| Casi pianificati per braccio | 24 |',
        '| A | '+', '.join(f'{k}: {v}' for k,v in g['QUALITY_PANEL_A'].items())+' |',
        '| B | '+', '.join(f'{k}: {v}' for k,v in g['QUALITY_PANEL_B'].items())+' |',
        f'| Coppie effettivamente valutabili | {s["evaluable_pairs"]}/24 |',
        f'| A FAIL / B PASS | {g["PAIRED_REGRESSIONS"]} |',
        f'| Regressioni critiche | {g["CRITICAL_REGRESSIONS"]} |',
        f'| Incompleti al cap | {g["INCOMPLETE_CASES"]} |',
        f'| Errori tecnici / casi non eseguiti | {g["TECHNICAL_ERRORS"]} |',
        f'| Validator bloccati / revisione / casi invalidi | {g["REVIEW_REQUIRED"]} |','',
        '## Tutte le coppie','', '| ID | Famiglia | A | B | Esito appaiato | Critico A / B |', '|---|---|---|---|---|---|']
    for p in s['pairs']:
        lines.append(f'| {p["case_id"]} | {p["family"]} | {p["A"]["status"]} | {p["B"]["status"]} | {p["pair_state"]} | {len(p["A"].get("critical_violations",[]))} / {len(p["B"].get("critical_violations",[]))} |')
    lines+=['','## Risultati per famiglia','', '| Famiglia | A | B | Coppie |','|---|---|---|---|']
    for f,v in s['per_family'].items():lines.append('| '+f+' | '+json.dumps(v['A'])+' | '+json.dumps(v['B'])+' | '+json.dumps(v['paired'])+' |')
    lines+=['','## Errori, regressioni e violazioni critiche','']
    problems=False
    for p in s['pairs']:
        if p['A']['status']=='PASS' and p['B']['status']=='PASS':continue
        problems=True;lines+=['### '+p['case_id']+' — '+p['pair_state'],'']
        for arm in ('A','B'):
            v=p[arm]
            lines.append(f'**{arm}: {v["status"]}.** '+v.get('reason',''))
            failed=[t['index'] for t in v.get('tests',[]) if not t['pass']]
            if failed:lines.append('Indici test indipendenti falliti (base 0): '+', '.join(map(str,failed))+'.')
            if v.get('critical_violations'):lines.append('Violazioni critiche: '+'; '.join(v['critical_violations'])+'.')
            if v.get('errors'):lines.append('Errori di integrità: '+'; '.join(v['errors'])+'.')
            if v.get('raw_path'):lines.append('Risposta originale: `'+v['raw_path']+'`.')
            lines.append('')
    if not problems:lines.append('Nessun fallimento sul pannello preregistrato. Questo non dimostra equivalenza generale o prontezza produzione.')
    lines+=['','## Provenienza, sanity e restore','']
    for arm,a in s['arms'].items():
        lines.append(f'- {arm}: `{a["run_id"]}`, {a["raw_records"]} record richieste incluse sanity, caricamenti {a["launch_count"]}; worker `{a["run_completion"]}`; sanity pre `{a["sanity"]["preflight"]["status"]}`, post `{a["sanity"]["postflight"]["status"]}`; restore `{a["restore_pass"]}`.')
        lines.append('  Raw SHA256: `'+str(a['raw_sha256'])+'`. Cleanup: `'+json.dumps(a['cleanup'],ensure_ascii=False)+'`.')
    lines+=['','Source index SHA256: `'+s['source_freeze']['index_sha256']+'`.',
            'Preregistrazione: `'+s['preregistration']['frozen_at']+'`. Una generazione per caso, EOS naturale, nessun best-of, correzione con feedback o replay.',
            '', 'Ultima verifica live: `'+json.dumps(s['final_live'],ensure_ascii=False)+'`.',
            '', '## Gate terminali','', '```json',json.dumps(g,indent=2,ensure_ascii=False),'```','',
            '## Limiti e utilizzo','',
            'Le risposte sono giudicate rispetto a specifiche, calcoli e unit test indipendenti, non rispetto al testo del riferimento B. Gli unit test di codice girano solo nel sandbox rootless Podman preregistrato, senza rete, mount host o GPU.',
            'Il pannello usa input brevi ed espliciti, per metà italiani e per metà inglesi. Non misura capacità su compiti aperti, contesti lunghi, concorrenza, tool reali o produzione. Le tool call dei casi diagnostici sono soltanto dati simulati.',
            'Un errore critico osservato esclude l’uso autonomo per quel tipo di compito. Anche tutti i casi PASS giustificherebbero soltanto una proposta di pilot circoscritto e supervisionato, mai una promozione automatica.',
            '', '## Riproduzione CPU-only','',
            '```bash','cd /home/funboy/StrixHaloMimo26','PYTHONDONTWRITEBYTECODE=1 python3 docs/mimo26/quality-retention-001/sources/evaluate.py --root docs/mimo26/quality-retention-001 --check','```',
            '', 'Il comando verifica gli hash e ricalcola i verdict senza inferenza, usando il medesimo sandbox disponibile e gli stessi validator congelati. `raw-results.jsonl` della consegna è un indice derivato delle risposte originali, non un log retrodatato.',
            '', '## Passo successivo proposto, non eseguito','',
            'Una campagna separata con casi holdout più realistici e preregistrati, concentrata sulle famiglie fallite o sui limiti non coperti; nessuna modifica di questo lotto dopo gli output.',
            '', 'PERF-BASELINE-001 resta terminale PARTIAL_ENGINE_DECODE_ONLY e non viene modificata da questi tempi diagnostici.','']
    return '\n'.join(lines)


def selftest():
    assert paired_state('PASS','PASS')=='BOTH_PASS'
    assert paired_state('FAIL_CODE_TEST','PASS')=='A_FAIL_B_PASS'
    assert paired_state('PASS','FAIL_SEMANTIC')=='A_PASS_B_FAIL'
    assert paired_state('FAIL_FORMAT','FAIL_CODE_TEST')=='BOTH_FAIL'
    for other in ('INCOMPLETE_OUTPUT_CAP','TECHNICAL_ERROR','TIMEOUT','VALIDATOR_BLOCKED','NEEDS_REVIEW','CASE_INVALID','NOT_RUN'):
        assert paired_state(other,'PASS')=='OTHER_STATES'
        assert paired_state('PASS',other)=='OTHER_STATES'
    demo=[{'A':'PASS','B':'PASS'}]*22+[{'A':'INCOMPLETE_OUTPUT_CAP','B':'PASS'},{'A':'PASS','B':'TECHNICAL_ERROR'}]
    assert len(demo)==24 and sum(paired_state(p['A'],p['B'])!='OTHER_STATES' for p in demo)==22
    print('PAIRED_EVALUATOR_SELFTEST_PASS: 20 pairing/denominator assertions, no inference')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path);group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--write',action='store_true');group.add_argument('--check',action='store_true');group.add_argument('--selftest',action='store_true');args=ap.parse_args()
    if args.selftest:selftest()
    else:
        if args.root is None:ap.error('--root required')
        summary,raw=evaluate(args.root);md=render(summary)
        pairs_text=''.join(json.dumps(p,sort_keys=True,ensure_ascii=False)+'\n' for p in summary['pairs'])
        raw_text=''.join(json.dumps(p,sort_keys=True,ensure_ascii=False)+'\n' for p in raw)
        if args.write:
            atomic(args.root/'summary.json',summary)
            (args.root/'REPORT.md').write_text(md)
            (args.root/'paired-results.jsonl').write_text(pairs_text)
            (args.root/'raw-results.jsonl').write_text(raw_text)
        else:
            assert json.loads((args.root/'summary.json').read_text())==summary,'SUMMARY_RECOMPUTATION_MISMATCH'
            assert (args.root/'REPORT.md').read_text()==md,'REPORT_RECOMPUTATION_MISMATCH'
            assert (args.root/'paired-results.jsonl').read_text()==pairs_text,'PAIRED_RECOMPUTATION_MISMATCH'
            assert (args.root/'raw-results.jsonl').read_text()==raw_text,'RAW_INDEX_RECOMPUTATION_MISMATCH'
        print(json.dumps({'status':'QUALITY_EVALUATION_WRITE_PASS' if args.write else 'QUALITY_EVALUATION_CHECK_PASS',
            'gates':summary['gates'],'paired':summary['pair_counts'],'regressions':summary['regressions']},indent=2))
