#!/usr/bin/env python3
from __future__ import annotations
import ast,json,os,re,signal,subprocess,time,urllib.request
from pathlib import Path
RUN=Path(os.environ['MIMO26_RUN_DIR'])
SERVER=os.environ['MIMO26_LLAMA_SERVER']
MODEL=os.environ['MIMO26_GGUF_FIRST_SHARD']
PORT=int(os.environ.get('MIMO26_PORT','18331'))
LOAD_TIMEOUT=float(os.environ.get('MIMO26_LOAD_TIMEOUT','600'))
HOST='127.0.0.1'; BASE='http://%s:%d'%(HOST,PORT); LOG=RUN/'server.log'
RUN.mkdir(parents=True,exist_ok=True)

def atomic(path,obj):
 q=path.with_suffix(path.suffix+'.tmp'); q.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n'); os.replace(q,path)
def meminfo():
 out={}
 for line in Path('/proc/meminfo').read_text().splitlines():
  if ':' in line:
   k,v=line.split(':',1); p=v.strip().split()
   if p and p[0].isdigit(): out[k]=int(p[0])*1024
 return out
def smaps(pid):
 out={}; p=Path('/proc/%d/smaps_rollup'%pid)
 if not p.exists(): return out
 for line in p.read_text().splitlines():
  if ':' in line:
   k,v=line.split(':',1); x=v.strip().split()
   if x and x[0].isdigit(): out[k]=int(x[0])*1024
 return out
def req(path,payload=None,timeout=10):
 data=None; headers={}
 if payload is not None:
  data=json.dumps(payload).encode(); headers['Content-Type']='application/json'
 r=urllib.request.Request(BASE+path,data=data,headers=headers,method='POST' if data is not None else 'GET')
 with urllib.request.urlopen(r,timeout=timeout) as resp:
  body=resp.read(); return resp.status,json.loads(body) if body else None
def code_gate(text):
 m=re.search(r'```(?:python)?\s*(.*?)```',text,flags=re.S|re.I); code=(m.group(1) if m else text).strip()
 try: tree=ast.parse(code)
 except Exception as e: return False,'parse:%s:%s'%(type(e).__name__,e)
 forbidden=(ast.Import,ast.ImportFrom,ast.Attribute,ast.With,ast.AsyncWith,ast.ClassDef,ast.Lambda,ast.Global,ast.Nonlocal,ast.Delete,ast.Try,ast.Raise,ast.While)
 if any(isinstance(n,forbidden) for n in ast.walk(tree)): return False,'forbidden_ast'
 funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
 if len(funcs)!=1 or funcs[0].name!='clamp': return False,'missing_clamp'
 if any(isinstance(n,ast.Call) for n in ast.walk(tree)): return False,'calls_not_allowed'
 ns={'__builtins__':{}}
 try:
  exec(compile(tree,'<mixed-sanity>','exec'),ns,ns); f=ns['clamp']
  for args,exp in [((5,0,10),5),((-1,0,10),0),((99,0,10),10),((3,3,3),3)]:
   got=f(*args)
   if got!=exp:return False,'unit_fail:%s:%s!=%s'%(args,got,exp)
 except Exception as e:return False,'exec:%s:%s'%(type(e).__name__,e)
 return True,'PASS'

pre=meminfo()
atomic(RUN/'load.json',{'status':'IN_PROGRESS','started_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'memory_before':pre,'model':MODEL})
cmd=[SERVER,'-m',MODEL,'--device','ROCm0','--split-mode','none','-ngl','all','-c','4096','-b','512','-ub','128','-np','1','--no-cont-batching','-fa','auto','--host',HOST,'--port',str(PORT),'--reasoning','off','--metrics']
log=LOG.open('w'); proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
stopping=False
def stop_server():
 global stopping
 if stopping:return
 stopping=True
 if proc.poll() is None:
  proc.terminate()
  try:proc.wait(timeout=20)
  except subprocess.TimeoutExpired:proc.kill();proc.wait()
def on_signal(sig,frame): stop_server(); raise SystemExit(128+sig)
signal.signal(signal.SIGTERM,on_signal); signal.signal(signal.SIGINT,on_signal)
start=time.monotonic(); last_err=''
while time.monotonic()-start<LOAD_TIMEOUT:
 if proc.poll() is not None:
  atomic(RUN/'load.json',{'status':'FAIL','cause':'SERVER_EXIT_%s'%proc.returncode,'load_s':time.monotonic()-start,'memory_before':pre,'server_log':str(LOG)})
  raise SystemExit(proc.returncode or 41)
 try:
  code,body=req('/health',timeout=2)
  if code==200: break
 except Exception as e:last_err='%s:%s'%(type(e).__name__,e)
 time.sleep(1)
else:
 atomic(RUN/'load.json',{'status':'FAIL','cause':'HEALTH_TIMEOUT','last_error':last_err,'load_s':time.monotonic()-start,'memory_before':pre,'server_log':str(LOG)})
 stop_server(); raise SystemExit(42)
load_s=time.monotonic()-start; post=meminfo(); sm=smaps(proc.pid)
try:
 _,models=req('/v1/models',timeout=5); model_id=models['data'][0]['id']
except Exception:model_id='mimo-mixed'
atomic(RUN/'load.json',{'status':'PASS','phase':'SERVER_HEALTHY','load_s':load_s,'pid':proc.pid,'model_id':model_id,'command':cmd,'memory_before':pre,'memory_after':post,'memavailable_delta_bytes':pre.get('MemAvailable',0)-post.get('MemAvailable',0),'process_smaps':sm,'server_log':str(LOG),'runtime_commit':'58367713a6935c0810103378144008df32e3d5db','finished_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'memory_accounting_note':'Host/UMA share physical memory; process PSS and MemAvailable delta are reported separately and are not summed.'})
specs=[
 ('arithmetic','Compute 17*19. Return only the integer.',lambda s:s=='323',64),
 ('extract','Read this exact token: ZEBRA-4821. Return only that token.',lambda s:s=='ZEBRA-4821',64),
 ('json','Return only valid JSON with exactly these values: alpha is integer 7 and beta is string "blue".',lambda s:json.loads(s)=={'alpha':7,'beta':'blue'},64),
 ('italian','Nel testo seguente il colore dichiarato è cobalto. Rispondi solo con il nome del colore.',lambda s:s.casefold()=='cobalto',64),
 ('english','Alice is first and Bob is second. Who is second? Return only the name.',lambda s:s=='Bob',64),
]
tests=[]
def persist(final=False):
 status=('PASS' if final and tests and all(x['pass'] for x in tests) else 'FAIL' if final else 'IN_PROGRESS')
 atomic(RUN/'quality.json',{'status':status,'thinking':False,'tests_completed':len(tests),'tests':tests,'persisted_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')})
persist()
for name,prompt,check,max_tokens in specs:
 payload={'model':model_id,'messages':[{'role':'user','content':prompt}],'temperature':0,'max_tokens':max_tokens,'stream':False}
 t=time.perf_counter()
 try:
  _,resp=req('/v1/chat/completions',payload,timeout=180); wall=time.perf_counter()-t
  choice=resp['choices'][0]; msg=choice['message']; text=(msg.get('content') or '').strip(); reasoning=msg.get('reasoning_content')
  try:ok=bool(check(text)); reason='PASS' if ok else 'expected_mismatch'
  except Exception as e:ok=False; reason='check:%s:%s'%(type(e).__name__,e)
  tests.append({'name':name,'prompt':prompt,'pass':ok,'reason':reason,'text':text,'reasoning_content':reasoning,'finish_reason':choice.get('finish_reason'),'wall_s':wall,'usage':resp.get('usage'),'raw_choice':choice})
 except Exception as e:
  tests.append({'name':name,'prompt':prompt,'pass':False,'reason':'request:%s:%s'%(type(e).__name__,e),'text':'','finish_reason':None})
 persist()

code_prompt='Return only Python code defining clamp(x, lo, hi). It must return lo when x < lo, hi when x > hi, otherwise x. Do not import anything and do not call other functions.'
payload={'model':model_id,'messages':[{'role':'user','content':code_prompt}],'temperature':0,'max_tokens':96,'stream':False}
t=time.perf_counter()
try:
 _,resp=req('/v1/chat/completions',payload,timeout=180); wall=time.perf_counter()-t
 choice=resp['choices'][0]; msg=choice['message']; text=(msg.get('content') or '').strip(); ok,reason=code_gate(text)
 tests.append({'name':'code_clamp','prompt':code_prompt,'pass':ok,'reason':reason,'text':text,'reasoning_content':msg.get('reasoning_content'),'finish_reason':choice.get('finish_reason'),'wall_s':wall,'usage':resp.get('usage'),'raw_choice':choice})
except Exception as e:
 tests.append({'name':'code_clamp','prompt':code_prompt,'pass':False,'reason':'request:%s:%s'%(type(e).__name__,e),'text':'','finish_reason':None})
persist(final=True)
quality_pass=all(x['pass'] for x in tests)
atomic(RUN/'model-result.json',{'schema':'mimo26-mixed-single-correctness-v1','quality_pass':quality_pass,'tests':tests,'load':json.loads((RUN/'load.json').read_text())})
stop_server(); log.close()
raise SystemExit(0 if quality_pass else 40)
