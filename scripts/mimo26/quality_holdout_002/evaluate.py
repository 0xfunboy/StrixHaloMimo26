"""Frozen paired evaluator/report generator. Reads persisted outputs, never invokes inference."""
from __future__ import annotations
import argparse
import collections
import copy
import json
import subprocess
from pathlib import Path
from common import atomic,digest,ids_sha,read_jsonl,sha,verify_freeze
from native_audit import load_arm,paired_state,EVALUABLE
from score import verdict
from validate import same

FAMILIES=('JSON','EVIDENCE','CONSTRAINT')


def decision(family,rows):
    """Predeclared qualitative decision policy, not a performance promotion threshold."""
    result={}
    for arm in ('A','B'):
        passed=[r['case_id'] for r in rows if r[arm]['status']=='PASS']
        failed=[r['case_id'] for r in rows if r[arm]['status'] in EVALUABLE and r[arm]['status']!='PASS']
        other=[r['case_id'] for r in rows if r[arm]['status'] not in EVALUABLE]
        critical=[r['case_id'] for r in rows if r[arm].get('critical_violations')]
        if other:status='EVIDENCE_INCOMPLETE_NO_FAMILY_PILOT_PROPOSAL'
        elif failed or critical:status='CONTAIN_OBSERVED_ERRORS_BEFORE_FAMILY_PILOT'
        else:status='SCOPED_SUPERVISED_PILOT_PROPOSAL_ONLY'
        result[arm]={'decision':status,'successful_case_types':passed,'errors_to_contain':failed,'incomplete_or_invalid':other,'critical_cases':critical}
    controls={
      'JSON':{'runtime_feasible':['strict parsing, duplicate/nonfinite rejection, schema and exact types','field invariants and recomputation from available input data'],
        'not_already_implemented':['task-specific semantic transformation checks without benchmark expected answers'],
        'scope':'A validator can reject malformed or inconsistent data; it does not create the correct missing answer.'},
      'EVIDENCE':{'runtime_feasible':['citation-ID existence, per-claim citation presence, record-scope and cutoff metadata checks'],
        'not_already_implemented':['semantic relevance, sufficient evidence coverage and contradictory-source resolution on unseen documents'],
        'scope':'Expected claim values and sufficient citation sets are benchmark oracles, not an existing production evidence judge.'},
      'CONSTRAINT':{'runtime_feasible':['feasibility and declared totals recalculated from the proposed plan and input constraints'],
        'not_already_implemented':['separate exact optimizer or optimality certificate for real problem sizes and tie-break rules'],
        'scope':'A feasibility checker rejects invalid choices; replacing a solution with a solver answer would be a different treatment.'}}
    return {'arms':result,'external_control_distinction':controls[family],
        'qualification':'Only six targeted synthetic cases in this family. No autonomous use, production deployment, model equivalence or automatic next experiment.'}


def compute(root):
    root=Path(root).resolve();freeze=verify_freeze(root)
    manifest=json.loads((root/'source-manifest.json').read_text());prep=json.loads((root/'preparation.json').read_text())
    assert manifest['campaign']=='QUALITY-HOLDOUT-002'
    assert prep['source_index_sha256']==freeze['index_sha256'],'PREPARATION_FREEZE_DISAGREEMENT'
    cases=read_jsonl(root/'cases.jsonl');sanity=read_jsonl(root/'sanity.jsonl');oracle_rows=read_jsonl(root/'expected.jsonl')
    oracles={o['case_id']:o for o in oracle_rows}
    assert len(cases)==18 and list(oracles)==manifest['case_order']==[c['case_id'] for c in cases]
    assert sum(c['output_cap'] for c in cases)==12288 and len(sanity)==6
    tokens=json.loads((root/'preflight/tokenization.json').read_text())
    results={};arms={};raw=[]
    for arm in ('A','B'):
        results[arm],arms[arm],records=load_arm(root,manifest,arm,cases,sanity)
        for r in records:raw.append({'aggregate_role':'DERIVED_INDEX_NOT_ORIGINAL_LOG','source_file':arms[arm]['raw_path'],'source_sha256':arms[arm]['raw_sha256'],'record':r})
        # The collector must have proven actual imports from the frozen source directory.
        imported=(arms[arm].get('load') or {}).get('source_freeze',{}).get('worker_loaded_modules',{})
        arms[arm]['frozen_import_paths_pass']=all(name in imported and imported[name]['sha256']==sha(root/'sources'/filename)
            for name,filename in [('common','common.py'),('validate','validate.py'),('__main__','adapter_'+arm.lower()+'.py')])
    peerpath=root/'evidence/B-rank1-raw-results.jsonl';peer=[];peer_ok=False;peer_errors=[]
    if peerpath.exists():
        peer=read_jsonl(peerpath);primary={(r['record']['phase'],r['record']['case_id']):r['record'] for r in raw if r['record']['arm']=='B'}
        peer_ok=len(peer)==len(primary)==30
        if not peer_ok:peer_errors.append('record cardinality not30')
        seen=set()
        for r in peer:
            identity=(r.get('phase'),r.get('case_id'));other=primary.get(identity)
            ok=identity not in seen and r.get('record_sha256')==digest({k:v for k,v in r.items() if k!='record_sha256'})
            seen.add(identity)
            ok=ok and other is not None and all(same(r.get(k),other.get(k)) for k in ('input_ids_provided','output_token_ids','output_tokens','final_text','finish_reason','completion_status','source_index_sha256'))
            ok=ok and r.get('rank')==1 and r.get('arm')=='B' and r.get('cache_reused_tokens')==0
            if not ok:peer_errors.append(str(identity))
            peer_ok=peer_ok and ok
        receipt=json.loads((root/'evidence/peer-copy-receipt.json').read_text())
        peer_ok=peer_ok and receipt.get('sha256')==sha(peerpath) and receipt.get('node')=='02-EVO-X3'
    arms['B']['peer_crosscheck']={'status':'PASS' if peer_ok else 'FAIL_OR_MISSING','records':len(peer),'errors':peer_errors,'sha256':sha(peerpath) if peerpath.exists() else None}
    reviews={}
    if (root/'case-invalid.json').exists():
        reviews=json.loads((root/'case-invalid.json').read_text())
        assert all(k in oracles and isinstance(v,str) and v.strip() for k,v in reviews.items()),'INVALID_CASE_REVIEW_FORMAT'
    pairs=[]
    for c in cases:
        o=oracles[c['case_id']];row={'case_id':c['case_id'],'family':c['family'],'language':c['language'],'title':c['title'],
            'input_tokens':c['input_tokens'],'output_cap':c['output_cap'],'oracle_sha256':digest(o)}
        scoring_error=None
        for arm in ('A','B'):
            item=results[arm][c['case_id']];v=copy.deepcopy(item['verdict'])
            if v['status']=='PENDING_INDEPENDENT_VALIDATION':
                try:scored=verdict(item['record']['final_text'],o,item['record']['completion_status'])
                except Exception as exc:
                    scoring_error=type(exc).__name__+':'+str(exc);scored={'status':'CASE_INVALID','reason':scoring_error,'critical_violations':[]}
                v.update(scored)
            row[arm]=v
        if c['case_id'] in reviews or scoring_error:
            for arm in ('A','B'):row[arm].update(status='CASE_INVALID',reason=reviews.get(c['case_id'],scoring_error),critical_violations=[])
        ra=results['A'][c['case_id']]['record'];rb=results['B'][c['case_id']]['record']
        row['input_ids_equal']=ra is not None and rb is not None and same(ra.get('input_ids_provided'),rb.get('input_ids_provided'))
        row['pair_state']=paired_state(row['A']['status'],row['B']['status'])
        row['critical_regression']=bool(row['A'].get('critical_violations')) and row['B']['status']=='PASS'
        pairs.append(row)
    family={}
    for name in FAMILIES:
        group=[r for r in pairs if r['family']==name]
        family[name]={'planned':6,'A':dict(collections.Counter(r['A']['status'] for r in group)),
            'B':dict(collections.Counter(r['B']['status'] for r in group)),
            'paired':dict(collections.Counter(r['pair_state'] for r in group)),'decision':decision(name,group)}
    live=json.loads((root/'final-live.json').read_text()) if (root/'final-live.json').exists() else {'status':'NOT_VERIFIED'}
    # Validate preregistration chronologically without reading live clocks into reproducible output.
    chronological={}
    from datetime import datetime
    frozen_at=datetime.fromisoformat(manifest['frozen_at'])
    for arm in ('A','B'):
        evpath=Path(manifest['runs'][arm]['run_dir'])/'events.jsonl';events=read_jsonl(evpath) if evpath.exists() else []
        starts=[e for e in events if e.get('event')=='RUN_START'];chronological[arm]=len(starts)==1 and frozen_at<datetime.fromisoformat(starts[0]['iso'])
    serial=False
    try:
        a_end=datetime.fromisoformat(arms['A']['cleanup']['at'])
        b_events=read_jsonl(Path(manifest['runs']['B']['run_dir'])/'events.jsonl')
        b_start=datetime.fromisoformat(next(e['iso'] for e in b_events if e['event']=='RUN_START'));serial=a_end<b_start
    except (KeyError,TypeError,StopIteration,FileNotFoundError):pass
    complete=all(arms[a]['raw_records']==30 and arms[a]['run_completion']=='PASS' and arms[a]['launch_count']==1 and not arms[a]['issues'] for a in ('A','B')) and peer_ok
    cache_ok=all(r['record'].get('cache_reused_tokens')==0 and r['record'].get('cache_gate_pass') is True for r in raw) and len(raw)==60
    input_ok=all(r['input_ids_equal'] for r in pairs) and not any(arms[a]['issues'] for a in ('A','B')) and peer_ok
    totals={a:dict(collections.Counter(r[a]['status'] for r in pairs)) for a in ('A','B')}
    critical_counts={a:sum(len(r[a].get('critical_violations',[])) for r in pairs) for a in ('A','B')}
    gates={'EXPERIMENT_COMPLETION':'COMPLETE' if complete else 'INCOMPLETE_OR_TECHNICAL',
        'PREREGISTRATION_AND_SOURCE_FREEZE':'PASS' if all(chronological.values()) and all(arms[a]['frozen_import_paths_pass'] for a in ('A','B')) else 'FAIL_OR_MISSING',
        'NATIVE_INPUT_COMPARABILITY':'PASS' if input_ok else 'FAIL_OR_MISSING','CACHE_REUSE_CHECK':'PASS_ZERO_REUSE' if cache_ok else 'FAIL_OR_MISSING',
        'SANITY_PRE':{a:arms[a]['sanity']['preflight']['status'] for a in ('A','B')},'SANITY_POST':{a:arms[a]['sanity']['postflight']['status'] for a in ('A','B')},
        'PANEL_A':totals['A'],'PANEL_B':totals['B'],'PAIRED_RESULTS':dict(collections.Counter(r['pair_state'] for r in pairs)),
        'CRITICAL_VIOLATIONS':critical_counts,'TECHNICAL_ERRORS':sum(r[a]['status'] in ('TECHNICAL_ERROR','TIMEOUT','VALIDATOR_BLOCKED') for r in pairs for a in ('A','B')),
        'INCOMPLETE':sum(r[a]['status'] in ('INCOMPLETE_OUTPUT_CAP','NOT_RUN') for r in pairs for a in ('A','B')),
        'CASE_INVALID':sum(r['A']['status']=='CASE_INVALID' or r['B']['status']=='CASE_INVALID' for r in pairs),
        'SERIAL_WINDOWS':'PASS' if serial else 'FAIL_OR_MISSING','RESTORE_STATUS':{**{a:'PASS' if arms[a]['restore_pass'] else 'FAIL_OR_MISSING' for a in ('A','B')},'final_live':live.get('status')},
        'GENERAL_EQUIVALENCE':'NOT_ESTABLISHED','QUANTIZATION_ONLY_EFFECT':'NOT_ISOLATED','PRODUCTION_PROMOTION':'NOT_PERFORMED',
        'THINKING_ON':'NOT_EVALUATED','LONG_CONTEXT':'NOT_EVALUATED','CONCURRENCY':'NOT_EVALUATED','MTP_DFLASH':'NOT_EVALUATED'}
    summary={'schema':'mimo26-holdout-summary-v1','campaign':'QUALITY-HOLDOUT-002','source_freeze':freeze,'preparation':prep,
        'planned_cases_per_arm':18,'primary_completions_including_sanity_per_arm':30,'evaluable_pairs':sum(r['pair_state']!='OTHER_STATES' for r in pairs),
        'pair_counts':gates['PAIRED_RESULTS'],'per_family':family,'gates':gates,'pairs':pairs,'arms':arms,'tokenization':tokens,
        'final_live':live,'preregistration_precedes_runs':chronological,'selection_bias':manifest['selection_bias'],
        'interpretation':'New targeted synthetic instances, families informed by001. Full configurations compared; original is not ground truth. No score combined with001.'}
    return summary,raw


def compact(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,allow_nan=False)


def error_description(v):
    d=v.get('diagnostics',{});parts=[]
    for e in d.get('schema_errors',[]):parts.append(e['path']+': '+e['issue'])
    if d.get('parse_error'):parts.append(d['parse_error'])
    for e in d.get('value_errors',[]):parts.append(e['path']+': atteso '+compact(e.get('expected'))+', ricevuto '+compact(e.get('actual')))
    for name,c in d.get('claims',{}).items():
        if c['pass']:continue
        issue=[]
        if not c['value_correct']:issue.append('valore '+compact(c['actual_value'])+' anziché '+compact(c['expected_value']))
        if c['nonexistent_ids']:issue.append('ID inesistenti '+compact(c['nonexistent_ids']))
        if c['irrelevant_or_superseded_ids']:issue.append('ID non pertinenti/superati '+compact(c['irrelevant_or_superseded_ids']))
        if not c['citations_sufficient']:issue.append('citazioni insufficienti '+compact(c['actual_citations'])+'; alternative sufficienti '+compact(c['sufficient_alternatives']))
        if c['duplicates']:issue.append('ID duplicati')
        parts.append(name+': '+'; '.join(issue))
    con=d.get('constraint')
    if con:
        parts.extend(con['violated_constraints'])
        for e in con['declared_total_mismatches']:parts.append(e['field']+': dichiarato '+str(e['declared'])+', ricalcolato '+str(e['recalculated']))
        if not con['optimality']:parts.append('ottimalità primaria non soddisfatta')
        if con['optimality'] and not con['tie_break']:parts.append('tie-break non soddisfatto')
        parts.append('ricalcolo indipendente: '+compact(con['recalculated']))
    if not parts:parts.append(v.get('reason',v['status']))
    return parts


def report(summary):
    g=summary['gates'];lines=['# StrixHaloMimo26 — QUALITY-HOLDOUT-002','',
        '**Esperimento: '+g['EXPERIMENT_COMPLETION']+'.** Score e completamento restano separati. Nessuna promozione o esperimento successivo.',
        '', '18 nuove fixture sintetiche: sei JSON, sei EVIDENCE, sei CONSTRAINT; 9 IT e9 EN. Famiglie scelte alla luce dei fallimenti001, non campione cieco rappresentativo.',
        'A: mixed Baekpica b3794b22, llama.cpp58367713 HIP, singolo Strix. B: Xiaomi5711b268 FP8/MXFP4, vLLM9255fd9 TP2, due Strix. Context4096, thinking OFF, nessuna grammar/repair/solver fornito al modello.',
        '', '## Risultati per famiglia', '', '| Famiglia | A | B | Coppie |', '|---|---|---|---|']
    for name,f in summary['per_family'].items():lines.append('| '+name+' | '+compact(f['A'])+' | '+compact(f['B'])+' | '+compact(f['paired'])+' |')
    lines+=['','Coppie valutabili: '+str(summary['evaluable_pairs'])+'/18. Nessun caso eliminato dal denominatore. Totali A: '+compact(g['PANEL_A'])+'; B: '+compact(g['PANEL_B'])+'.',
        '', '## Tutte le18 coppie', '', '| Caso | Input token | Cap | A | B | Coppia |', '|---|---:|---:|---|---|---|']
    for r in summary['pairs']:lines.append(f'| {r["case_id"]} | {r["input_tokens"]} | {r["output_cap"]} | {r["A"]["status"]} | {r["B"]["status"]} | {r["pair_state"]} |')
    lines+=['','## Errori e diagnostiche', '']
    for r in summary['pairs']:
        if r['A']['status']=='PASS' and r['B']['status']=='PASS':continue
        lines+=['### '+r['case_id']+' — '+r['title'],'']
        for arm in ('A','B'):
            v=r[arm];lines+=['**'+arm+': '+v['status']+'**. '+('Nessun errore osservato nel caso.' if v['status']=='PASS' else ' '.join(error_description(v))),
                'Fonte: `'+v.get('raw_path','NOT_RUN')+'`.']
            if v.get('critical_violations'):lines.append('Violazioni critiche preregistrate: '+compact(v['critical_violations']))
        lines.append('')
    lines+=['## Decisione per famiglia, senza esecuzione di pilot','']
    for name,f in summary['per_family'].items():
        d=f['decision'];lines+=['### '+name,'']
        for arm,v in d['arms'].items():lines.append(arm+': **'+v['decision']+'**. Casi riusciti: '+compact(v['successful_case_types'])+'. Errori da contenere: '+compact(v['errors_to_contain'])+'. Altri stati: '+compact(v['incomplete_or_invalid'])+'.')
        control=d['external_control_distinction']
        lines+=['Controlli eseguibili sui dati reali: '+'; '.join(control['runtime_feasible'])+'.',
            'Componenti dedicati ancora necessari, non implementati in produzione: '+'; '.join(control['not_already_implemented'])+'.',control['scope'],d['qualification'],'']
    lines+=['## Provenienza e budget','', 'Commit preparazione: `'+summary['preparation']['preparation_commit']+'`.',
        'Indice frozen SHA256: `'+summary['source_freeze']['index_sha256']+'`. Sorgenti/validator/oracoli/configurazioni congelati prima di entrambi i run.',
        'Per ogni famiglia quattro cap512 e due cap1024; massimo12288 output token per braccio, esclusi sanity. Ogni input+cap+256 <=4096; nessun input troncato.',
        'Input effettivi e scostamenti dai range indicativi sono in preflight/tokenization.json. Nessun padding aggiunto per raggiungere un numero.',
        'Ogni risposta naturale è giudicata da specifiche indipendenti. L’originale non definisce expected o citazioni ammesse. I due algoritmi esatti CONSTRAINT concordano prima dei modelli; almeno un caso è INFEASIBLE.',
        'Nessun codice generato sul nodo host: il solo codice sanity viene testato nel sandbox rootless Podman qualificato, senza rete/mount host/GPU. I piani sono dati, non azioni.',
        '', '## Sanity e restore','']
    for arm,m in summary['arms'].items():lines.append(arm+': `'+m['run_id']+'`, '+str(m['raw_records'])+' record primari, caricamenti '+str(m['launch_count'])+', sanity pre/post '+m['sanity']['preflight']['status']+'/'+m['sanity']['postflight']['status']+', cleanup '+compact(m['cleanup'])+'.')
    lines+=['Il peer B è confrontato con i30 record primari e non conta come replica. Dettagli NODE01/NODE02 e timestamp separati in final-live.json.',
        'Stato finale: '+compact(summary['final_live'])+'.','', '## Gate terminali','', '```json',json.dumps(g,ensure_ascii=False,indent=2),'```',
        '', '## Ricalcolo CPU-only effettivo', '', '```bash','cd /home/funboy/StrixHaloMimo26',
        'PYTHONDONTWRITEBYTECODE=1 python3 docs/mimo26/quality-holdout-002/sources/evaluate.py --root docs/mimo26/quality-holdout-002 --check','```',
        'Richiede gli artefatti originali nei percorsi del manifest e l’immagine Podman pinned localmente disponibile per i sanity. Non è una promessa di portabilità. Il ricalcolo non invia richieste ai modelli.',
        'REPORT.md, summary.json, paired-results.jsonl e FINDINGS.md sono generati dalla stessa base canonica. raw-results.jsonl è un indice derivato dichiarato; i raw originali sono preservati.',
        'La ricevuta CPU_RECALCULATION_CHECK è in verification.json, prodotta dal comando --check senza modificarne i risultati.',
        '', 'PERF-BASELINE-001 resta terminale PARTIAL_ENGINE_DECODE_ONLY; QUALITY-RETENTION-001 resta completata e separata. I tempi incidentali non sono un nuovo benchmark.',
        '**Fine mandato:** consegna locale e stop. Nessun pilot, deployment, push, tuning o ulteriore esperimento automatico.','']
    return '\n'.join(lines)


def outputs(summary,raw):
    markdown=report(summary)
    findings='# Decisioni e diagnostiche — QUALITY-HOLDOUT-002\n\n'+markdown.split('## Errori e diagnostiche',1)[1].split('## Provenienza e budget',1)[0]
    return {'summary.json':json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n',
        'paired-results.jsonl':''.join(compact(r)+'\n' for r in summary['pairs']),
        'raw-results.jsonl':''.join(compact(r)+'\n' for r in raw),'REPORT.md':markdown,'FINDINGS.md':findings}


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--write',action='store_true');g.add_argument('--check',action='store_true');args=p.parse_args()
    summary,raw=compute(args.root);artifacts=outputs(summary,raw)
    if args.write:
        for name,content in artifacts.items():(args.root/name).write_text(content)
    else:
        for name,content in artifacts.items():assert (args.root/name).read_text()==content,'RECALCULATION_MISMATCH:'+name
    print(json.dumps({'status':'HOLDOUT_EVALUATION_WRITE_PASS' if args.write else 'HOLDOUT_EVALUATION_CHECK_PASS','gates':summary['gates'],'per_family':{k:{'A':v['A'],'B':v['B']} for k,v in summary['per_family'].items()}},indent=2))


if __name__=='__main__':main()
