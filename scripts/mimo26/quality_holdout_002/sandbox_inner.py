"""Executed ONLY inside the preregistered rootless Podman sandbox via stdin."""
from __future__ import annotations
import ast
import builtins
import copy
import json
import os
import resource
import socket
import sys

resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
resource.setrlimit(resource.RLIMIT_FSIZE, (1048576,1048576))
resource.setrlimit(resource.RLIMIT_NOFILE, (64,64))
resource.setrlimit(resource.RLIMIT_AS, (201326592,201326592))


def same(a,b):
    if type(a) is not type(b): return False
    if isinstance(a,dict): return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)): return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b


def guard(code):
    tree=ast.parse(code)
    if not all(isinstance(n,ast.FunctionDef) or (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)) for n in tree.body):
        raise ValueError('only function definitions and docstrings allowed at module level')
    forbidden=(ast.Import,ast.ImportFrom,ast.ClassDef,ast.Global,ast.Nonlocal,ast.With,ast.AsyncWith,ast.AsyncFunctionDef)
    denied={'exec','eval','open','compile','input','print','breakpoint','exit','quit','globals','locals','vars','getattr','setattr','delattr','help','dir','memoryview'}
    for n in ast.walk(tree):
        if isinstance(n,forbidden):raise ValueError('forbidden syntax: '+type(n).__name__)
        if isinstance(n,ast.FunctionDef) and n.decorator_list:raise ValueError('decorators forbidden')
        if isinstance(n,ast.Name) and (n.id.startswith('__') or n.id in denied):raise ValueError('forbidden name')
        if isinstance(n,ast.Attribute) and n.attr.startswith('_'):raise ValueError('private/dunder attributes forbidden')
    return tree


def probe():
    results={}
    for name,addr in [('cluster',('127.0.0.1',18221)),('peer',('10.55.0.2',18220))]:
        s=socket.socket();s.settimeout(.3)
        results[name]=s.connect_ex(addr);s.close()
    root_write=False
    try:
        with open('/should_not_be_writable','w') as f:f.write('probe')
        root_write=True
    except OSError:pass
    status=open('/proc/self/status').read()
    r={'uid':os.getuid(),'home_exists':os.path.exists('/home/funboy'),'root_ssh_exists':os.path.exists('/root/.ssh'),
       'netns':os.readlink('/proc/self/ns/net'),'network_connect_codes':results,
       'root_writable':root_write,'devices':sorted(os.listdir('/dev')),'env_keys':sorted(os.environ),
       'memory_limit':open('/sys/fs/cgroup/memory.max').read().strip(),
       'pids_limit':open('/sys/fs/cgroup/pids.max').read().strip(),
       'cap_eff_zero':'CapEff:\t0000000000000000' in status,'no_new_privs':'NoNewPrivs:\t1' in status}
    r['pass']=(r['uid']==65534 and not r['home_exists'] and not r['root_ssh_exists'] and not root_write
        and all(x!=0 for x in results.values()) and 'kfd' not in r['devices'] and 'dri' not in r['devices']
        and r['memory_limit']=='268435456' and r['pids_limit']=='32' and r['cap_eff_zero'] and r['no_new_privs'])
    return r


def main():
    payload=json.loads(sys.stdin.read(131072))
    if payload.get('mode')=='probe': return {'mode':'probe','probe':probe()}
    tree=guard(payload['code'])
    names=('abs','all','any','divmod','pow','iter','repr','format','ord','chr','frozenset','hash','callable','bytes','bytearray','bool','dict','enumerate','filter','float','int','isinstance','issubclass','len','list','map','max','min','next','range','reversed','round','set','slice','sorted','str','sum','tuple','type','zip','ValueError','TypeError','KeyError','IndexError','Exception','StopIteration')
    ns={'__builtins__':{k:getattr(builtins,k) for k in names}}
    exec(compile(tree,'<isolated-candidate>','exec'),ns,ns)
    fn=ns.get(payload['function'])
    if not callable(fn):return {'status':'FAIL_CODE_TEST','reason':'requested_function_missing','tests':[]}
    tests=[]
    for i,t in enumerate(payload['tests']):
        args=copy.deepcopy(t['args']); original=copy.deepcopy(args)
        try:
            value=fn(*args)
            ok='raises' not in t and same(value,t.get('expected'))
            detail={'actual_type':type(value).__name__,'actual_preview':repr(value)[:700]}
        except BaseException as e:
            ok=t.get('raises')==type(e).__name__
            detail={'exception':type(e).__name__,'message':str(e)[:300]}
        unchanged=same(args,original)
        if payload.get('check_input_immutability',True):ok=ok and unchanged
        tests.append({'index':i,'pass':ok,'input_unchanged':unchanged,**detail})
    return {'status':'PASS' if all(t['pass'] for t in tests) and tests else 'FAIL_CODE_TEST','tests':tests}

try:
    answer=main()
except BaseException as e:
    answer={'status':'FAIL_CODE_TEST','reason':type(e).__name__+':'+str(e)[:600],'tests':[]}
print(json.dumps(answer,ensure_ascii=False,allow_nan=False))
