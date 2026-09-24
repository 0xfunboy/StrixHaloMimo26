"""Executed only inside the pinned rootless container, never on the host."""
import ast
import builtins
import copy
import json
import math
import os
import resource
import sys
import types

resource.setrlimit(resource.RLIMIT_CPU,(3,3))
resource.setrlimit(resource.RLIMIT_FSIZE,(1048576,1048576))
resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def same(a,b):
    return type(a) is type(b) and (a.keys()==b.keys() and all(same(a[k],b[k]) for k in a) if isinstance(a,dict) else len(a)==len(b) and all(same(x,y) for x,y in zip(a,b)) if isinstance(a,(list,tuple)) else a==b)


def normalized(x):
    if isinstance(x,set):return sorted(x)
    if isinstance(x,tuple):return [normalized(v) for v in x]
    if isinstance(x,list):return [normalized(v) for v in x]
    if isinstance(x,dict):return {k:normalized(v) for k,v in x.items()}
    return x


def probe():
    import socket
    codes={}
    for label,host in [('local','127.0.0.1'),('peer','10.55.0.2')]:
        s=socket.socket();s.settimeout(.2)
        try:codes[label]=s.connect_ex((host,18221))
        finally:s.close()
    return {'uid':os.getuid(),'host_home_present':os.path.exists('/home/funboy'),'devices':os.listdir('/dev'),'network_connect_codes':codes,'environment_keys':sorted(os.environ),'netns':os.readlink('/proc/self/ns/net'),'capability_status':[x for x in open('/proc/self/status').read().splitlines() if x.startswith(('CapEff:','NoNewPrivs:'))]}


def main(payload):
    if payload.get('mode')=='probe':return {'status':'PASS','probe':probe()}
    files=payload['files'];order=payload['file_order'];tests=payload['tests']
    if set(files)!=set(order):return {'status':'FAIL_FORMAT','reason':'file names differ','tests':[]}
    if sum(len(x) for x in files.values())>65536:return {'status':'FAIL_FORMAT','reason':'code too large','tests':[]}
    modules={name[:-3]:types.ModuleType(name[:-3]) for name in order}
    allowed_imports=set(modules)
    safe_names=['abs','all','any','bool','dict','divmod','enumerate','filter','float','frozenset','int','isinstance','issubclass','iter','len','list','map','max','min','next','pow','range','repr','reversed','round','set','slice','sorted','str','sum','tuple','type','zip','ValueError','TypeError','KeyError','IndexError','Exception','RuntimeError','StopIteration']
    safe={name:getattr(builtins,name) for name in safe_names}
    loaded=set()
    def limited_import(name,globals=None,locals=None,fromlist=(),level=0):
        if level or name not in loaded:raise ImportError('only earlier task modules may be imported')
        return modules[name]
    safe['__import__']=limited_import
    for name in order:
        source=files[name]
        if type(source) is not str:return {'status':'FAIL_FORMAT','reason':'source must be string','tests':[]}
        try:tree=ast.parse(source,filename=name)
        except SyntaxError as e:return {'status':'FAIL_FORMAT','reason':'syntax: '+str(e),'tests':[]}
        blocked=(ast.ClassDef,ast.AsyncFunctionDef,ast.Await,ast.Global,ast.Nonlocal,ast.With,ast.AsyncWith)
        for node in ast.walk(tree):
            if isinstance(node,blocked):return {'status':'FAIL_CODE_TEST','reason':'unsupported unsafe AST '+type(node).__name__,'tests':[]}
            if isinstance(node,ast.Name) and node.id.startswith('__'):return {'status':'FAIL_CODE_TEST','reason':'dunder name forbidden','tests':[]}
            if isinstance(node,ast.Attribute) and node.attr.startswith('_'):return {'status':'FAIL_CODE_TEST','reason':'private attribute forbidden','tests':[]}
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[x.name for x in node.names] if isinstance(node,ast.Import) else [node.module]
                if any(n not in allowed_imports for n in names) or getattr(node,'level',0):return {'status':'FAIL_CODE_TEST','reason':'outside import forbidden','tests':[]}
            if isinstance(node,ast.FunctionDef) and node.decorator_list:return {'status':'FAIL_CODE_TEST','reason':'decorators forbidden','tests':[]}
        for node in tree.body:
            if not isinstance(node,(ast.FunctionDef,ast.Import,ast.ImportFrom,ast.Assign,ast.AnnAssign,ast.Expr)):
                return {'status':'FAIL_CODE_TEST','reason':'unexpected top-level statement','tests':[]}
            if isinstance(node,ast.Expr) and not (isinstance(node.value,ast.Constant) and isinstance(node.value.value,str)):
                return {'status':'FAIL_CODE_TEST','reason':'top-level execution forbidden','tests':[]}
        namespace=modules[name[:-3]].__dict__;namespace['__builtins__']=dict(safe)
        try:exec(compile(tree,name,'exec'),namespace,namespace)
        except Exception as e:return {'status':'FAIL_CODE_TEST','reason':'module: '+type(e).__name__+':'+str(e)[:500],'tests':[]}
        loaded.add(name[:-3])
    results=[]
    for index,test in enumerate(tests):
        args=copy.deepcopy(test['args'])
        for i in test.get('set_args',[]):args[i]=set(args[i])
        before=copy.deepcopy(args);result=None;error=None
        try:
            mod,func=test['function'].split('.')
            result=modules[mod].__dict__[func](*args)
        except Exception as e:error=type(e).__name__
        unchanged=same(args,before)
        if 'error' in test:ok=error==test['error']
        else:ok=error is None and same(normalized(result),test['expected'])
        if error is None and 'new_result_from_args' in test:
            ok=ok and type(result) is dict and all(result is not args[i] for i in test['new_result_from_args'])
        if error is None and 'new_pair_from_args' in test:
            ok=ok and type(result) is tuple and len(result)==2 and type(result[0]) is dict and type(result[1]) is set
            if ok:ok=all(result[k] is not args[i] for k,i in enumerate(test['new_pair_from_args']))
        ok=ok and unchanged
        results.append({'index':index,'pass':bool(ok),'input_unchanged':unchanged,'error':error,'actual':normalized(result) if error is None else None})
    return {'status':'PASS' if all(t['pass'] for t in results) else 'FAIL_CODE_TEST','tests':results}

try:
    payload=json.load(sys.stdin)
    result=main(payload)
    print(json.dumps(result,allow_nan=False))
except BaseException as exc:
    print(json.dumps({'status':'VALIDATOR_BLOCKED','reason':type(exc).__name__+':'+str(exc)[:1000]}))
