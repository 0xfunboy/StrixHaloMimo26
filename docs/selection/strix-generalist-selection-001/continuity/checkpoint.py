"""Read-only run reconciliation plus factual documentary checkpoint; never dispatches."""
from pathlib import Path
import argparse
import datetime
import json
import sys
import time

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
sys.path.insert(0,str(ROOT/'sources'))
from common import atomic
from window_guards import unit_state,controller_status


def snapshot():
    m=json.loads((ROOT/'source-manifest.json').read_text());info=dict(m['runs'])
    info['T']=json.loads((ROOT/'continuity/addendum.json').read_text())['mtp_run']
    if (ROOT/'recovery-D/preparation.json').exists():
        info['D_SETUP']=dict(info['D'])
        info['D']=json.loads((ROOT/'recovery-D/manifest.json').read_text())['run']
    out={'observed_at':datetime.datetime.now().astimezone().isoformat(),'host':'01-EVO-X3','profiles':{}}
    for key,cfg in info.items():
        r=Path(cfg['run_dir']);row={'run_id':cfg['run_id'],'run_dir':str(r),'exists':r.exists(),'unit':unit_state(cfg['supervisor_unit'])}
        for name in ['result.json','load.json','panel-progress.json','progress-rank0.json','fatal.json','mtp-off-blocker.json','sanity-pre.json','sanity-post.json']:
            p=r/name
            if not p.exists():continue
            d=json.loads(p.read_text())
            if name=='result.json':row.update(completion=d.get('run_completion'),initial_cause=d.get('initial_cause'),cleanup=d.get('cleanup'))
            elif name=='load.json':row['load']={k:d.get(k) for k in ['status','load_s','pid','error']}
            elif name.startswith('sanity-'):row[name]={'status':d.get('status'),'cases':len(d.get('tests',[]))}
            else:row[name]=d
        p=r/'raw-results.jsonl'
        if p.exists():
            rows=[json.loads(line) for line in p.read_text().splitlines() if line.strip()]
            row['primary_records']=len(rows)
            row['panel']=[{k:d.get(k) for k in ['case_id','request_id','completion_status','output_tokens','final_chars','request_latency_s']} for d in rows if d['phase']=='panel']
        for side in ['off','on']:
            p=r/('mtp-'+side)/'summary.json'
            if p.exists():
                d=json.loads(p.read_text());row['mtp-'+side]={k:d.get(k) for k in ['status','records','partial_acceptance_observed','equivalence']}
        out['profiles'][key]=row
    out['controller']=controller_status()
    return out


def signature(d):
    return json.dumps({k:{x:v.get(x) for x in ['exists','completion','cleanup','primary_records','load','fatal.json','mtp-off-blocker.json','mtp-off','mtp-on']} for k,v in d['profiles'].items()},sort_keys=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--wait-change',type=int,default=0);p.add_argument('--persist',action='store_true');p.add_argument('--brief',action='store_true');a=p.parse_args()
    first=snapshot();data=first;deadline=time.monotonic()+min(max(a.wait_change,0),100)
    while time.monotonic()<deadline:
        time.sleep(min(5,max(0,deadline-time.monotonic())))
        data=snapshot()
        if signature(data)!=signature(first):break
    if a.persist:
        atomic(ROOT/'continuity/last-observed.json',data)
        lines=['# STRIX-GENERALIST-SELECTION-001: verified checkpoint','', 'Observed: '+data['observed_at'],
               'Base: 87442a8e1b999e5f33165d0b6b563eac5248ab15. Continuity: efae11dae82e322f581db0de1d3ad0226e5ce37d.',
               'Source indexes and all 74+15 preregistered files remain unchanged. See preparation.json, continuity/preparation.json, QWEN_HISTORY_AND_REUSE.md.','']
        for key,row in data['profiles'].items():
            lines += ['## '+key+' / '+row['run_id'],json.dumps({k:row.get(k) for k in ['exists','completion','load','primary_records','cleanup','fatal.json','mtp-off-blocker.json']},ensure_ascii=False),
                      'Unit: '+json.dumps(row['unit']), 'Raw: '+row['run_dir'],'']
        lines += ['## Resident',json.dumps(data['controller']), '',
                  'NEXT EXACT ACTION: reconcile the earliest existing nonterminal run and its supervised restore. Never replay an uncertain request or redispatch an existing run. Once terminal/restored, continue only the remaining authorized Q/M/D/O/T order through launch_continuity_v1.py; technical failures require an explicit isolated blocker. After all permitted windows, CPU audit/evaluation and local delivery; no new experiment. No push/deployment, tuning, new download or changes to resident releases. K2 EngineCore processes after restore are legitimate residents.']
        (ROOT/'HANDOFF.md').write_text('\n'.join(lines)+'\n')
    if a.brief:
        brief={'observed_at':data['observed_at'],'controller':data['controller'],'profiles':{}}
        for k,v in data['profiles'].items():
            brief['profiles'][k]={x:v.get(x) for x in ['run_id','exists','completion','load','primary_records','panel-progress.json','progress-rank0.json','fatal.json','mtp-off-blocker.json']}
            brief['profiles'][k]['unit']=v['unit'];brief['profiles'][k]['cleanup']={x:(v.get('cleanup') or {}).get(x) for x in ['status','at','epoch']}
        print(json.dumps(brief,indent=2))
    else:print(json.dumps(data,indent=2))

if __name__=='__main__':main()
