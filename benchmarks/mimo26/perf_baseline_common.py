#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, ast
from pathlib import Path

def atomic_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    q=path.with_suffix(path.suffix+".tmp")
    q.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n")
    os.replace(q,path)

def meminfo() -> dict[str,int]:
    out={}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" not in line: continue
        k,v=line.split(":",1); p=v.strip().split()
        if p and p[0].isdigit(): out[k]=int(p[0])*1024
    return out

def vmstat() -> dict[str,int]:
    out={}
    for line in Path("/proc/vmstat").read_text().splitlines():
        p=line.split()
        if len(p)==2 and p[1].isdigit() and p[0] in {"pgfault","pgmajfault","pswpin","pswpout"}:
            out[p[0]]=int(p[1])
    return out

def proc_io(pid:int) -> dict[str,int]:
    out={}
    try:
        for line in Path(f"/proc/{pid}/io").read_text().splitlines():
            if ":" in line:
                k,v=line.split(":",1)
                if v.strip().isdigit(): out[k]=int(v.strip())
    except FileNotFoundError: pass
    return out

def proc_status(pid:int) -> dict[str,str]:
    out={}
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if ":" in line:
                k,v=line.split(":",1)
                if k in {"VmRSS","VmSize","VmSwap","RssAnon","RssFile"}: out[k]=v.strip()
    except FileNotFoundError: pass
    return out

def hwmon() -> dict[str,int|str]:
    base=Path("/sys/class/hwmon")
    for d in base.glob("hwmon*"):
        try:name=(d/"name").read_text().strip()
        except Exception:continue
        if name=="amdgpu":
            out={"hwmon":str(d),"name":name}
            for f in ("temp1_input","freq1_input","power1_average","power1_input"):
                p=d/f
                try:out[f]=int(p.read_text().strip())
                except Exception:pass
            return out
    return {}

def netdev(iface:str="thunderbolt0") -> dict[str,int]:
    out={}
    root=Path("/sys/class/net")/iface/"statistics"
    for k in ("rx_bytes","tx_bytes","rx_packets","tx_packets","rx_errors","tx_errors"):
        try:out[k]=int((root/k).read_text().strip())
        except Exception:pass
    return out

def code_gate(text:str):
    m=re.search(r"```(?:python)?\s*(.*?)```",text,flags=re.S|re.I)
    code=(m.group(1) if m else text).strip()
    try:tree=ast.parse(code)
    except Exception as e:return False,f"parse:{type(e).__name__}:{e}"
    forbidden=(ast.Import,ast.ImportFrom,ast.Attribute,ast.With,ast.AsyncWith,ast.ClassDef,ast.Lambda,ast.Global,ast.Nonlocal,ast.Delete,ast.Try,ast.Raise,ast.While)
    if any(isinstance(n,forbidden) for n in ast.walk(tree)):return False,"forbidden_ast"
    funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
    if len(funcs)!=1 or funcs[0].name!="clamp":return False,"missing_clamp"
    if any(isinstance(n,ast.Call) for n in ast.walk(tree)):return False,"calls_not_allowed"
    ns={"__builtins__":{}}
    try:
        exec(compile(tree,"<sanity>","exec"),ns,ns); f=ns["clamp"]
        for args,exp in [((5,0,10),5),((-1,0,10),0),((99,0,10),10),((3,3,3),3)]:
            if f(*args)!=exp:return False,f"unit_fail:{args}"
    except Exception as e:return False,f"exec:{type(e).__name__}:{e}"
    return True,"PASS"

SANITY=[
 ("arithmetic","Compute 17*19. Return only the integer.",lambda s:s=="323",64),
 ("extract","Read this exact token: ZEBRA-4821. Return only that token.",lambda s:s=="ZEBRA-4821",64),
 ("json",'Return only valid JSON with exactly these values: alpha is integer 7 and beta is string "blue".',lambda s:json.loads(s)=={"alpha":7,"beta":"blue"},64),
 ("italian","Nel testo seguente il colore dichiarato è cobalto. Rispondi solo con il nome del colore.",lambda s:s.casefold()=="cobalto",64),
 ("english","Alice is first and Bob is second. Who is second? Return only the name.",lambda s:s=="Bob",64),
]
CODE_PROMPT="Return only Python code defining clamp(x, lo, hi). It must return lo when x < lo, hi when x > hi, otherwise x. Do not import anything and do not call other functions."
