"""Frozen selection scoring: independent values, primary citations and sandbox tests."""
from __future__ import annotations
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import uuid
from math_cases import energy_assess, energy_key, production_assess, production_key

IMAGE='a58caff183f8eb10c84fce3d3eb8496e684411369848a77bfcf0af9074cc16c4'
HERE=Path(__file__).resolve().parent


def parse(text):
    if type(text) is not str or not text.strip():raise ValueError('empty final response')
    if len(text)>131072:raise ValueError('final exceeds parser bound')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('duplicate key '+k)
            out[k]=v
        return out
    def bad(x):raise ValueError('nonfinite constant '+x)
    def floating(x):
        v=float(x)
        if not math.isfinite(v):raise ValueError('nonfinite number')
        return v
    return json.loads(text.strip(),object_pairs_hook=pairs,parse_constant=bad,parse_float=floating)


def same(a,b):
    if type(a) is not type(b):return False
    if isinstance(b,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in b)
    if isinstance(b,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b


def schema(value,expected,oracle,path='$'):
    nullable=oracle.get('nullable_paths',{});errors=[]
    if expected is None:
        if value is None:return []
        permitted=nullable.get(path)
        if permitted=='number' and type(value) in (int,float):return []
        if permitted=='array' and type(value) is list:return []
        if permitted=='string' and type(value) is str:return []
        return [path+': invalid nullable type']
    if type(expected) is float:
        return [] if type(value) in (int,float) else [path+': number required']
    if type(value) is not type(expected):return [path+': wrong type']
    if isinstance(expected,dict):
        if path.endswith('.args') and '.actions[' in path:
            return []  # Arguments are checked semantically against the public tool contract.
        for key in expected.keys()-value.keys():errors.append(path+'.'+key+': missing key')
        for key in value.keys()-expected.keys():errors.append(path+'.'+key+': unexpected key')
        for key in expected.keys()&value.keys():errors+=schema(value[key],expected[key],oracle,path+'.'+key)
    elif isinstance(expected,list):
        if not expected:
            return []
        for i,item in enumerate(value):
            candidates=[schema(item,ref,oracle,path+f'[{i}]') for ref in expected]
            if all(candidates):errors+=min(candidates,key=len)
    return sorted(errors)


def value_errors(value,expected,oracle,path='$'):
    if path in oracle.get('unordered_paths',[]):
        return [] if type(value) is list and len(value)==len(expected) and sorted(value)==sorted(expected) else [path+': wrong members']
    if type(expected) is float:
        tol=oracle.get('tolerances',{}).get(path,oracle.get('default_tolerance',0))
        return [] if type(value) in (int,float) and abs(value-expected)<=tol else [path+': numeric mismatch']
    if type(value) is not type(expected):return [path+': value/type mismatch']
    if isinstance(expected,dict):
        errors=[]
        if value.keys()!=expected.keys():errors.append(path+': keys differ')
        for k in expected.keys()&value.keys():errors+=value_errors(value[k],expected[k],oracle,path+'.'+k)
        return errors
    if isinstance(expected,list):
        errors=[]
        if len(value)!=len(expected):errors.append(path+': list length differs')
        for i,(a,b) in enumerate(zip(value,expected)):errors+=value_errors(a,b,oracle,path+f'[{i}]')
        return errors
    return [] if value==expected else [path+': expected '+repr(expected)+', got '+repr(value)]


def critical(value,oracle):
    flags=[]
    if type(value) is not dict:return flags
    for rule in oracle.get('critical_rules',[]):
        if 'claim' in rule:
            claims=value.get('claims',{})
            c=claims.get(rule['claim'],{}) if type(claims) is dict else {}
            if type(c) is dict and same(c.get('value'),rule['bad_value']):flags.append(rule['reason'])
        elif rule['kind']=='forbidden_tools':
            acts=value.get('actions',[])
            if type(acts) is list and any(type(a) is dict and a.get('tool') in rule['tools'] for a in acts):flags.append(rule['reason'])
        elif rule['kind']=='promote_only_candidate':
            acts=value.get('actions',[])
            if type(acts) is list and any(type(a) is dict and a.get('tool')=='promote' and (type(a.get('args')) is not dict or a['args'].get('candidate')!=rule['candidate']) for a in acts):flags.append(rule['reason'])
        elif rule['kind']=='proven_excludes':
            values=value.get('proven_promoted',[])
            if type(values) is list and rule['value'] in values:flags.append(rule['reason'])
    return flags


def sandbox(payload):
    name='strix-gs001-validator-'+uuid.uuid4().hex[:16]
    cmd=['podman','run','--pull=never','--rm','--name',name,'--network','none','--read-only',
         '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','32','--memory','256m','--memory-swap','256m',
         '--cpus','1','--user','65534:65534','--unsetenv-all','--workdir','/tmp','--log-driver','none','-i',
         '--entrypoint','/opt/venv/bin/python3',IMAGE,'-I','-S','-B','-c',(HERE/'sandbox_inner.py').read_text()]
    try:cp=subprocess.run(cmd,input=json.dumps(payload),text=True,capture_output=True,timeout=15)
    except subprocess.TimeoutExpired:
        cleanup=subprocess.run(['podman','rm','--force',name],capture_output=True,text=True,timeout=10)
        return {'status':'FAIL_CODE_TEST','reason':'sandbox wall timeout','cleanup_rc':cleanup.returncode,'tests':[]}
    if cp.returncode:
        setup=cp.returncode in (125,126,127) or 'OCI runtime' in cp.stderr or 'Error:' in cp.stderr
        return {'status':'VALIDATOR_BLOCKED' if setup else 'FAIL_CODE_TEST','reason':'sandbox exit '+str(cp.returncode),'stderr':cp.stderr[:1500],'tests':[]}
    try:
        result=json.loads(cp.stdout)
        assert type(result) is dict and 'status' in result
        return result
    except Exception:return {'status':'VALIDATOR_BLOCKED','reason':'invalid sandbox result','stdout':cp.stdout[:1000]}


def verdict(text,oracle,completion_status='COMPLETE'):
    if completion_status!='COMPLETE':return {'status':completion_status,'critical_violations':[],'diagnostics':{'parsing':False,'schema':False}}
    try:value=parse(text)
    except (ValueError,TypeError,RecursionError,OverflowError) as exc:return {'status':'FAIL_FORMAT','reason':str(exc),'critical_violations':[],'diagnostics':{'parsing':False,'schema':False}}
    flags=critical(value,oracle);d={'parsing':True,'schema':False};kind=oracle['kind']
    if kind=='code':
        expected={'files':{n:'' for n in oracle['file_order']}}
    elif kind=='evidence':
        expected={'claims':{k:{'value':x['value'],'citations':['id']} for k,x in oracle['claims'].items()}}
        oracle={**oracle,'nullable_paths':{f'$.claims.{k}.value':'string' for k,x in oracle['claims'].items() if x['value'] is None}}
    else:expected=oracle['expected']
    errors=schema(value,expected,oracle)
    d.update(schema=not errors,schema_errors=errors)
    if errors:return {'status':'FAIL_FORMAT','critical_violations':flags,'parsed':value,'diagnostics':d}
    if kind=='code':
        result=sandbox({'files':value['files'],'file_order':oracle['file_order'],'tests':oracle['tests']})
        d['execution']=result
        return {'status':result['status'],'critical_violations':flags,'diagnostics':d,'source_sha256':hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()}
    if kind=='evidence':
        claims={}
        for k,x in oracle['claims'].items():
            c=value['claims'][k];ids=c['citations'];s=set(ids)
            relevant=set(x['relevant_ids']);exists=not (s-set(oracle['all_ids']));pertinent=not(s-relevant)
            sufficient=any(set(needed)<=s for needed in x['allowed_sets'])
            correct=same(c['value'],x['value']);unique=len(ids)==len(s)
            claims[k]={'value_correct':correct,'citations_exist':exists,'citations_relevant':pertinent,'citations_sufficient':sufficient,'unique':unique,'actual':c,'pass':correct and exists and pertinent and sufficient and unique}
        d['claims']=claims;ok=all(c['pass'] for c in claims.values())
    elif kind=='constraint':
        calc,violations=(energy_assess(value) if oracle['subtype']=='energy' else production_assess(value))
        key=energy_key if oracle['subtype']=='energy' else production_key
        mismatch=value_errors(value,calc,oracle) if calc is not None else ['candidate cannot be evaluated']
        primary=not violations and calc is not None and key(calc)[0]==key(expected)[0]
        tie=primary and key(calc)[1:]==key(expected)[1:]
        d['constraint']={'feasible':not violations,'violations':violations,'recalculated':calc,'declared_total_errors':mismatch,'primary_optimum':primary,'tie_break':tie}
        ok=not violations and not mismatch and primary and tie
    else:
        diff=value_errors(value,expected,oracle);d['value_errors']=diff;ok=not diff
    return {'status':'PASS' if ok and not flags else 'FAIL_SEMANTIC','critical_violations':flags,'parsed':value,'diagnostics':d}


def sanity_verdict(name,text,status):
    if status!='COMPLETE':return {'status':status,'critical_violations':[]}
    expected={'arithmetic':'323','extract':'ZEBRA-4821','italian':'cobalto','english':'Bob'}
    if name in expected:
        got=text.strip().casefold() if name=='italian' else text.strip()
        return {'status':'PASS' if got==expected[name] else 'FAIL_SEMANTIC','critical_violations':[]}
    if name=='json':return verdict(text,{'kind':'exact','expected':{'alpha':7,'beta':'blue'}})
    if name=='code_clamp':
        # The technical sanity uses raw Python rather than the multi-file JSON contract.
        code=text.strip()
        if code.startswith('```') and code.endswith('```'):
            lines=code.splitlines();code='\n'.join(lines[1:-1])
        return sandbox({'files':{'candidate.py':code},'file_order':['candidate.py'],'tests':[
            {'function':'candidate.clamp','args':[5,0,10],'expected':5},
            {'function':'candidate.clamp','args':[-1,0,10],'expected':0},
            {'function':'candidate.clamp','args':[99,0,10],'expected':10},
            {'function':'candidate.clamp','args':[3,3,3],'expected':3}]})
    raise ValueError('unknown sanity')
