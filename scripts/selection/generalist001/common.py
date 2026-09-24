"""Durable collection helpers; imports do not initialize any inference runtime."""
from __future__ import annotations
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

CAMPAIGN='STRIX-GENERALIST-SELECTION-001'


def now():return time.strftime('%Y-%m-%dT%H:%M:%S%z')
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def digest(obj):return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def ids_sha(ids):return hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest()
def read_jsonl(path):return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def atomic(path,obj,exclusive=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(obj,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
        if exclusive:os.link(temp,path)
        else:os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def append(path,obj):
    with Path(path).open('a') as f:
        f.write(json.dumps(obj,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())


def verify_freeze(root):
    root=Path(root).resolve();files=[]
    for line in (root/'source-SHA256SUMS').read_text().splitlines():
        expected,relative=line.split('  ',1);p=(root/relative).resolve()
        if not p.is_relative_to(root):raise ValueError('unsafe index path')
        if sha(p)!=expected:raise RuntimeError('SOURCE_FREEZE_MISMATCH:'+relative)
        files.append(relative)
    imported={}
    if os.environ.get('GS_ROOT'):
        for name in ['__main__','common','validate']:
            module=sys.modules.get(name)
            if module is None:raise RuntimeError('REQUIRED_IMPORT_MISSING:'+name)
            p=Path(module.__file__).resolve()
            if p.parent!=root/'sources':raise RuntimeError('WORKER_IMPORT_OUTSIDE_FREEZE:'+name)
            imported[name]={'path':str(p),'sha256':sha(p)}
    return {'status':'PASS','files_checked':len(files),'index_sha256':sha(root/'source-SHA256SUMS'),'loaded_modules':imported}


def plain(value):
    if value is None or type(value) in (str,int,float,bool):return value
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    if isinstance(value,dict):return {str(k):plain(v) for k,v in value.items()}
    if dataclasses.is_dataclass(value):return plain(dataclasses.asdict(value))
    if hasattr(value,'__dict__'):return {'_native_type':type(value).__name__,**plain(vars(value))}
    raise TypeError('unsupported native value '+type(value).__name__)


def snapshot(pid=None):
    pid=pid or os.getpid();mem={};proc={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        k,raw=line.split(':',1)
        if k in ('MemAvailable','MemTotal','SwapFree','SwapTotal'):mem[k]=int(raw.split()[0])*1024
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            k,_,v=line.partition(':')
            if k in ('VmRSS','VmSwap','VmSize'):proc[k]=int(v.split()[0])*1024
        stat=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        proc.update(pid=pid,minflt=int(stat[7]),majflt=int(stat[9]),starttime_ticks=int(stat[19]))
        proc['io']={k:int(v) for k,v in (line.split(':',1) for line in Path(f'/proc/{pid}/io').read_text().splitlines())}
    except (OSError,ValueError):proc['snapshot_unavailable']=True
    gpu=[]
    for vendor in Path('/sys/class/drm').glob('card*/device/vendor'):
        try:
            if vendor.read_text().strip()!='0x1002':continue
            dev=vendor.parent;item={'device':str(dev),'values':{}}
            for name in ['gpu_busy_percent','pp_dpm_sclk','pp_dpm_mclk']:
                p=dev/name
                try:item['values'][name]=p.read_text().strip()
                except OSError:pass
            for p in dev.glob('hwmon/hwmon*/*_input'):
                if p.name.startswith(('temp','power','freq')):
                    try:item['values'][str(p.relative_to(dev))]=p.read_text().strip()
                    except OSError:pass
            gpu.append(item)
        except OSError:pass
    return {'observed_at':now(),'memory_bytes':mem,'process':proc,'gpu_sysfs':gpu,'resource_scope':'Point snapshots, not continuous peaks or proof of no throttling'}


def split_reasoning(text,ids,mode,profile,tokenizer=None):
    """Split at actual control tokens; never force a missing closing boundary."""
    eos=set(profile.get('eos_ids',[]))
    def decode(part):
        kept=[i for i in part if i not in eos]
        return tokenizer.decode(kept,skip_special_tokens=False) if tokenizer is not None else None
    if not mode:
        final=decode(ids) if ids is not None and tokenizer is not None else text
        return {'reasoning_text':'','final_text':final,'reasoning_closed':True,'reasoning_observed':False,
                'reasoning_tokens_native':0 if ids is not None else None,
                'final_tokens_native':None if ids is None else sum(i not in profile['eos_ids'] for i in ids),
                'boundary_method':'thinking-disabled'}
    op=profile.get('think_open_id');cl=profile.get('think_close_id');prefilled=profile.get('thinking_prefix_open',False)
    if ids is None:raise ValueError('native API with separate reasoning must use native fields')
    opened=prefilled or op in ids
    if not opened:
        if '<think>' in text or '</think>' in text:raise ValueError('text/ID reasoning boundary disagreement')
        final=decode(ids) if tokenizer is not None else text
        return {'reasoning_text':'','final_text':final,'reasoning_closed':True,'reasoning_observed':False,
                'reasoning_tokens_native':0,'final_tokens_native':sum(i not in profile['eos_ids'] for i in ids),
                'boundary_method':'native-no-reasoning-block-emitted'}
    begin=0 if prefilled else ids.index(op)+1
    try:end=ids.index(cl,begin)
    except ValueError:end=None
    if end is None:
        reason=decode(ids[begin:]) if tokenizer is not None else text.removeprefix('<think>') if not prefilled else text
        return {'reasoning_text':reason,'final_text':'','reasoning_closed':False,'reasoning_observed':True,
                'reasoning_tokens_native':sum(i not in profile['eos_ids'] for i in ids[begin:]),'final_tokens_native':0,
                'boundary_method':'native-reasoning-unclosed'}
    if tokenizer is not None:
        reason=decode(ids[begin:end]);final=decode(ids[end+1:])
    else:
        if '</think>' not in text:raise ValueError('native closing token not represented in raw text')
        before,final=text.split('</think>',1)
        reason=before if prefilled else before.split('<think>',1)[1] if '<think>' in before else None
        if reason is None:raise ValueError('native opening token not represented in raw text')
    return {'reasoning_text':reason,'final_text':final,'reasoning_closed':True,'reasoning_observed':True,
            'reasoning_tokens_native':sum(i not in profile['eos_ids'] and i not in (op,cl) for i in ids[begin:end]),
            'final_tokens_native':sum(i not in profile['eos_ids'] for i in ids[end+1:]),
            'boundary_method':'native-control-token-boundary'}


def completion_state(finish,count,cap,final,phase):
    if finish is None or type(count) is not int or count<0:return 'TECHNICAL_ERROR'
    if phase in ('benchmark','warmup','mtp_equivalence','mtp_benchmark'):
        if finish not in ('eos','stop','word','limit','length','max_tokens'):return 'TECHNICAL_ERROR'
        if count<cap:return 'SHORT_OUTPUT' if phase in ('benchmark','warmup','mtp_benchmark') else 'COMPLETE'
        return 'VALID_CAP' if count==cap else 'OVER_OUTPUT'
    if finish in ('length','limit','max_tokens') or count>=cap:return 'INCOMPLETE_OUTPUT_CAP'
    if finish not in ('eos','stop','word'):return 'TECHNICAL_ERROR'
    if not final.strip():return 'INCOMPLETE_NO_FINAL'
    return 'COMPLETE'


def begin_request(root,run,case,profile,rank,phase):
    request_id=f'{run.name}/{profile}/{phase}/{case["request_key"]}'
    dest=run/('requests' if rank==0 else 'requests-rank'+str(rank))/(phase+'__'+case['request_key'])
    dest.mkdir(parents=True,exist_ok=True)
    atomic(dest/'intent.json',{'campaign':CAMPAIGN,'run_id':run.name,'request_id':request_id,'case_id':case['case_id'],
           'request_key':case['request_key'],'profile':profile,'rank':rank,'phase':phase,'state':'IN_FLIGHT','at':now(),
           'source_index_sha256':sha(root/'source-SHA256SUMS'),'input_ids_sha256':case['input_ids_sha256']},exclusive=True)
    return request_id,dest


def base_record(root,run,case,profile,rank,phase,request_id):
    return {'schema':'strix-generalist-request-v1','campaign':CAMPAIGN,'run_id':run.name,'request_id':request_id,
            'case_id':case['case_id'],'request_key':case['request_key'],'profile':profile,'rank':rank,'phase':phase,
            'messages':case['messages'],'rendered_text':case['rendered_text'],'input_token_ids':case['input_token_ids'],
            'input_ids_sha256':case['input_ids_sha256'],'input_tokens':len(case['input_token_ids']),
            'output_cap':case['output_cap'],'thinking':case['thinking'],'sampling':case['sampling'],
            'timeout_s':case['timeout_s'],'source_index_sha256':sha(root/'source-SHA256SUMS')}


def persist_result(dest,record,run,rank):
    record['persisted_at']=now();record['record_sha256']=digest(record)
    atomic(dest/'result.json',record,exclusive=True)
    append(run/('raw-results.jsonl' if rank==0 else 'rank'+str(rank)+'-raw-results.jsonl'),record)
    atomic(run/('progress-rank'+str(rank)+'.json'),{'last_request':record['request_id'],'phase':record['phase'],'case_id':record['case_id'],
           'completion_status':record['completion_status'],'updated_at':now()})


def error_record(record,exc,elapsed=None):
    return {**record,'completion_status':'TIMEOUT' if isinstance(exc,TimeoutError) else 'TECHNICAL_ERROR',
            'error':type(exc).__name__+':'+str(exc)[:2000],'native_response':record.get('native_response'),'final_text':'','reasoning_text':'',
            'output_token_ids':None,'output_tokens':None,'finish_reason':None,'request_latency_s':elapsed}
