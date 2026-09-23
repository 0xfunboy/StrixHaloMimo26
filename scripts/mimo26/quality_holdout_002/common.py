"""Pure-stdlib collection helpers for the new nonstreaming quality campaign."""
from __future__ import annotations
import dataclasses
import hashlib
import json
import os
import time
import sys
import tempfile
from pathlib import Path

CAMPAIGN='QUALITY-HOLDOUT-002'
SAMPLING={'temperature':0.0,'seed':1,'repetition_penalty':1.0,'presence_penalty':0.0,
          'frequency_penalty':0.0,'ignore_eos':False,'thinking':False,'prefix_reuse':False}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def ids_sha(ids):return hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest()
def now():return time.strftime('%Y-%m-%dT%H:%M:%S%z')
def read_jsonl(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def atomic(path,obj,exclusive=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    data=json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    if exclusive:
        # Publish a complete, fsynced file without replacing any existing result.
        fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
        try:
            with os.fdopen(fd,'w') as f:f.write(data);f.flush();os.fsync(f.fileno())
            os.link(tmp,path)  # atomic exclusive publication; EEXIST refuses replay
        finally:
            os.unlink(tmp)
    else:
        tmp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
        with tmp.open('w') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def append(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:
        f.write(json.dumps(obj,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())


def verify_freeze(root):
    root=Path(root); checks=[]
    for line in (root/'source-SHA256SUMS').read_text().splitlines():
        expected,rel=line.split('  ',1)
        p=root/rel
        if not p.resolve().is_relative_to(root.resolve()):raise ValueError('unsafe source index path')
        actual=sha(p)
        if actual!=expected:raise RuntimeError('SOURCE_FREEZE_MISMATCH:'+rel)
        checks.append(rel)
    loaded={}
    if os.environ.get('QR_ROOT'):
        for name in ('common','validate','__main__'):
            module=sys.modules[name];p=Path(module.__file__).resolve()
            if p.parent!=(root/'sources').resolve():raise RuntimeError('WORKER_IMPORT_NOT_FROZEN:'+str(p))
            loaded[name]={'path':str(p),'sha256':sha(p)}
    return {'status':'PASS','files_checked':len(checks),'index_sha256':sha(root/'source-SHA256SUMS'),'worker_loaded_modules':loaded}



def snapshot(pid=None):
    pid=pid or os.getpid();mem={};proc={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key,raw=line.split(':',1)
        if key in ('MemAvailable','MemTotal','SwapFree','SwapTotal'):
            mem[key]=int(raw.split()[0])*1024
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            key,_,value=line.partition(':')
            if key in ('VmRSS','VmSwap','VmSize'):proc[key]=int(value.split()[0])*1024
        stat=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        proc.update(pid=pid,minflt=int(stat[7]),majflt=int(stat[9]))
        proc['io']={k:int(v) for k,v in (line.split(':',1) for line in Path(f'/proc/{pid}/io').read_text().splitlines())}
    except (OSError,ValueError):proc['snapshot_unavailable']=True
    return {'observed_at':now(),'mem_bytes':mem,'process':proc}


def completion_state(finish,count,cap,has_result=True):
    if not has_result or finish is None or type(count) is not int or count<0:return 'TECHNICAL_ERROR'
    if finish in ('length','limit','max_tokens') or count>=cap:return 'INCOMPLETE_OUTPUT_CAP'
    if finish in ('stop','eos','word'):return 'COMPLETE'
    return 'TECHNICAL_ERROR'


def plain(value):
    if value is None or isinstance(value,(str,int,float,bool)):return value
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    if isinstance(value,dict):return {str(k):plain(v) for k,v in value.items()}
    if dataclasses.is_dataclass(value):return plain(dataclasses.asdict(value))
    if hasattr(value,'__dict__'):return {'_native_type':type(value).__name__,**plain(vars(value))}
    raise TypeError('unsupported native output field type '+type(value).__name__)


def begin_request(run,case,arm,rank,phase,root):
    request_id=f'{run.name}/{arm}/{phase}/{case["case_id"]}'
    dest=run/('requests' if rank==0 else f'requests-rank{rank}')/(phase+'__'+case['case_id'])
    dest.mkdir(parents=True,exist_ok=True)
    intent={'campaign':CAMPAIGN,'run_id':run.name,'request_id':request_id,'case_id':case['case_id'],
        'arm':arm,'rank':rank,'phase':phase,'state':'IN_FLIGHT','created_at':now(),
        'source_index_sha256':sha(root/'source-SHA256SUMS'),'input_ids_sha256':ids_sha(case['input_token_ids']),
        'output_cap':case['output_cap'],'sampling':SAMPLING}
    atomic(dest/'intent.json',intent,exclusive=True)
    return request_id,dest


def base_result(run,case,arm,rank,phase,request_id,root):
    return {'schema':'mimo26-quality-request-v1','campaign':CAMPAIGN,'run_id':run.name,
        'request_id':request_id,'case_id':case['case_id'],'arm':arm,'rank':rank,'phase':phase,
        'family':case.get('family','sanity'),'language':case.get('language'),
        'messages':case['messages'],'rendered_text':case['rendered_text'],
        'rendered_text_sha256':case['rendered_text_sha256'],
        'input_ids_provided':case['input_token_ids'],'input_tokens':len(case['input_token_ids']),
        'input_ids_sha256':ids_sha(case['input_token_ids']), 'output_cap':case['output_cap'],
        'sampling':SAMPLING,'source_index_sha256':sha(root/'source-SHA256SUMS')}


def persist_result(dest,result,run,rank):
    result['persisted_at']=now()
    result['record_sha256']=digest(result)
    atomic(dest/'result.json',result,exclusive=True)
    append(run/('raw-results.jsonl' if rank==0 else f'rank{rank}-raw-results.jsonl'),result)
    atomic(run/(f'progress-rank{rank}.json'),{'campaign':CAMPAIGN,'run_id':run.name,'arm':result['arm'],
        'last_request':result['request_id'],'phase':result['phase'],'last_case':result['case_id'],
        'last_completion_status':result['completion_status'],'updated_at':now()})


def failure_record(base,exc):
    return {**base,'completion_status':'TIMEOUT' if isinstance(exc,TimeoutError) else 'TECHNICAL_ERROR',
        'error':type(exc).__name__+':'+str(exc)[:2500],'native_response':None,'output_token_ids':None,
        'output_tokens':None,'final_text':'','finish_reason':None}
