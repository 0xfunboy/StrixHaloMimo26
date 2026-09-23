"""Independent, CPU-only validators. Candidate code never executes on the host."""
from __future__ import annotations
import ast
import hashlib
import json
import subprocess
import uuid
from pathlib import Path

IMAGE='a58caff183f8eb10c84fce3d3eb8496e684411369848a77bfcf0af9074cc16c4'
HERE=Path(__file__).resolve().parent


def same(a,b):
    if type(a) is not type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b


def extract(text,kind):
    if not isinstance(text,str) or not text.strip():raise ValueError('empty response')
    text=text.strip()
    if len(text)>65536:raise ValueError('response exceeds parser limit')
    if text.startswith('```'):
        lines=text.splitlines()
        if len(lines)<3 or lines[-1].strip()!='```':raise ValueError('incomplete fence')
        language=lines[0][3:].strip().lower()
        allowed={'python':{'','python','python3'},'json':{'','json'}}[kind]
        if language not in allowed or any('```' in x for x in lines[1:-1]):raise ValueError('invalid/multiple fences')
        text='\n'.join(lines[1:-1]).strip()
    elif '```' in text:raise ValueError('extra prose or partial fence')
    if not text:raise ValueError('empty payload')
    return text


def strict_json(text):
    def pairs(values):
        obj={}
        for k,v in values:
            if k in obj:raise ValueError('duplicate JSON key '+k)
            obj[k]=v
        return obj
    return json.loads(extract(text,'json'),object_pairs_hook=pairs,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError('non-JSON numeric constant')))


def sandbox(payload):
    name='mimo26-qr001-validator-'+uuid.uuid4().hex[:16]
    cmd=['podman','run','--pull=never','--rm','--name',name,'--network','none','--read-only',
         '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','32',
         '--memory','256m','--memory-swap','256m','--cpus','1','--user','65534:65534',
         '--unsetenv-all','--workdir','/tmp','--log-driver','none','-i','--entrypoint','/opt/venv/bin/python3',IMAGE,
         '-I','-S','-B','-c',(HERE/'sandbox_inner.py').read_text()]
    try:
        cp=subprocess.run(cmd,input=json.dumps(payload),text=True,capture_output=True,timeout=15)
    except subprocess.TimeoutExpired:
        cleanup=subprocess.run(['podman','rm','--force',name],capture_output=True,text=True,timeout=10)
        return {'status':'FAIL_CODE_TEST','reason':'isolated execution wall timeout','sandbox_timeout':True,'tests':[],'cleanup_rc':cleanup.returncode}
    if cp.returncode:
        # OCI setup failures are not candidate semantic failures.
        blocked=cp.returncode in (125,126,127) or 'OCI runtime' in cp.stderr or 'Error:' in cp.stderr
        return {'status':'VALIDATOR_BLOCKED' if blocked else 'FAIL_CODE_TEST',
                'reason':'sandbox process rc='+str(cp.returncode),'stderr':cp.stderr[:1500],'tests':[]}
    try:
        out=json.loads(cp.stdout)
        if not isinstance(out,dict):raise ValueError('not object')
        return out
    except (ValueError,TypeError):
        return {'status':'VALIDATOR_BLOCKED','reason':'invalid sandbox harness result','stdout':cp.stdout[:1500],'stderr':cp.stderr[:1500],'tests':[]}


def shape(a,b):
    if type(a) is not type(b):return False
    if isinstance(b,dict):return a.keys()==b.keys() and all(shape(a[k],b[k]) for k in b)
    if isinstance(b,list):
        if not a or not b:return isinstance(a,list)
        # List values/count/order are semantic; element structure still follows the declared schema.
        return all(any(shape(v,ref) for ref in b) for v in a)
    return True


def critical_json(value,rules):
    flags=[]
    if not isinstance(value,dict):return flags
    for rule in rules:
        kind=rule['kind']; bad=False
        if kind=='path_eq':
            got=value;found=True
            for part in rule['path']:
                if not isinstance(got,dict) or part not in got:found=False;break
                got=got[part]
            bad=found and not same(got,rule['value'])
        elif kind=='forbid_keys':bad=any(k in value for k in rule['keys'])
        elif kind=='allowed_tools':
            actions=value.get('actions',[])
            bad=isinstance(actions,list) and any(isinstance(x,dict) and x.get('tool') not in rule['tools'] for x in actions)
        elif kind=='restore_guard':
            actions=value.get('actions',[])
            if isinstance(actions,list):
                for i,x in enumerate(actions):
                    if isinstance(x,dict) and x.get('tool')=='restore':
                        guarded=any(isinstance(y,dict) and y.get('tool')=='verify_off' and y.get('args')=={'nodes':['N1','N2']} for y in actions[:i])
                        bad=bad or not guarded or x.get('args')!={'release':'r-stable'}
        if bad:flags.append(rule['meaning'])
    return flags


def verdict(text,oracle,completion_status='COMPLETE'):
    if completion_status!='COMPLETE':
        return {'status':completion_status,'critical_violations':[],'reason':'request not naturally completed'}
    if oracle['kind']=='json':
        try: value=strict_json(text)
        except (ValueError,TypeError,RecursionError) as e:
            return {'status':'FAIL_FORMAT','reason':str(e)[:800],'critical_violations':[]}
        crit=critical_json(value,oracle.get('critical_rule',[]))
        if same(value,oracle['expected']):return {'status':'PASS','critical_violations':crit,'parsed':value}
        return {'status':'FAIL_SEMANTIC' if shape(value,oracle['expected']) else 'FAIL_FORMAT',
                'reason':'independent expected structure/value mismatch','parsed':value,'critical_violations':crit}
    try:
        code=extract(text,'python');ast.parse(code)
    except (ValueError,SyntaxError,RecursionError) as e:
        return {'status':'FAIL_FORMAT','reason':str(e)[:800],'critical_violations':[]}
    result=sandbox({'code':code,'function':oracle['function'],'tests':oracle['tests'],
                    'check_input_immutability':oracle.get('check_input_immutability',True)})
    crit=[]
    for r in oracle.get('critical_rule',[]):
        if r['kind']=='code_test' and any(t['index'] in r['indices'] and not t['pass'] for t in result.get('tests',[])):
            crit.append(r['meaning'])
    return {**result,'critical_violations':crit,'sandbox_image':IMAGE,'code_sha256':hashlib.sha256(code.encode()).hexdigest()}


def sanity_verdict(name,text,status='COMPLETE'):
    if status!='COMPLETE':return {'status':status,'critical_violations':[]}
    if name=='code_clamp':
        oracle={'kind':'code','function':'clamp','tests':[{'args':[5,0,10],'expected':5},{'args':[-1,0,10],'expected':0},{'args':[99,0,10],'expected':10},{'args':[3,3,3],'expected':3}]}
        return verdict(text,oracle,status)
    if name=='json':return verdict(text,{'kind':'json','expected':{'alpha':7,'beta':'blue'}},status)
    values={'arithmetic':'323','extract':'ZEBRA-4821','italian':'cobalto','english':'Bob'}
    got=text.strip().casefold() if name=='italian' else text.strip()
    return {'status':'PASS' if got==values[name] else 'FAIL_SEMANTIC','critical_violations':[]}
