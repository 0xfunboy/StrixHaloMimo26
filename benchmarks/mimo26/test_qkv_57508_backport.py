#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import torch
from safetensors import safe_open

BLOCK=128
FP8=torch.float8_e4m3fn
FP8_MAX=torch.finfo(FP8).max
COLS=128
TOL=0.06

ROOT=Path("/home/funboy/StrixHaloMimo26")
MODEL=Path("/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL")

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

new=load_module("mimo26_patch_new", ROOT/"benchmarks/mimo26/vllm_patch.py")
old=load_module("mimo26_patch_old", ROOT/"benchmarks/mimo26/regressions/vllm_patch_global_qkv_wrong.py")

GEOMS={
    "full":(64,4,192,128,4),
    "swa":(64,8,192,128,4),
}

def cdiv(a,b): return (a+b-1)//b

def chunk_rows(nh,nk,hd,vd,ckpt_tp):
    return (nh//ckpt_tp)*hd+(nk//ckpt_tp)*hd+(nk//ckpt_tp)*vd

def manual_quantize_chunks(truth,nh,nk,hd,vd,ckpt_tp):
    rows=chunk_rows(nh,nk,hd,vd,ckpt_tp)
    weights=[]; scales=[]
    for c in range(ckpt_tp):
        x=truth[c*rows:(c+1)*rows].clone()
        q=torch.empty_like(x,dtype=FP8)
        s=torch.empty((cdiv(rows,BLOCK),x.shape[1]//BLOCK),dtype=torch.float32)
        for r in range(0,rows,BLOCK):
            for col in range(0,x.shape[1],BLOCK):
                block=x[r:r+BLOCK,col:col+BLOCK]
                scale=(block.abs().max().clamp(min=1e-12)/FP8_MAX).float()
                s[r//BLOCK,col//BLOCK]=scale
                q[r:r+BLOCK,col:col+BLOCK]=(block/scale).to(FP8)
        weights.append(q); scales.append(s)
    return torch.cat(weights,0),torch.cat(scales,0)

def owned_indices(nh,nk,hd,vd,ckpt_tp,tp_rank,tp_size):
    rows=chunk_rows(nh,nk,hd,vd,ckpt_tp)
    qpc=(nh//ckpt_tp)*hd
    kpc=(nk//ckpt_tp)*hd
    qhpc=nh//ckpt_tp
    kvhpc=nk//ckpt_tp
    qheads=list(range(tp_rank*(nh//tp_size),(tp_rank+1)*(nh//tp_size)))
    if tp_size<=nk:
        kvheads=list(range(tp_rank*(nk//tp_size),(tp_rank+1)*(nk//tp_size)))
    else:
        kvheads=[tp_rank//(tp_size//nk)]
    idx=[]
    for h in qheads:
        c,o=divmod(h,qhpc); start=c*rows+o*hd
        idx.extend(range(start,start+hd))
    for h in kvheads:
        c,o=divmod(h,kvhpc); start=c*rows+qpc+o*hd
        idx.extend(range(start,start+hd))
    for h in kvheads:
        c,o=divmod(h,kvhpc); start=c*rows+qpc+kpc+o*vd
        idx.extend(range(start,start+vd))
    return torch.tensor(idx,dtype=torch.long)

def dequant_output(w,s):
    rows=w.shape[0]
    scale_rows=s.repeat_interleave(BLOCK,0)[:rows]
    scale_full=scale_rows.repeat_interleave(BLOCK,1)[:,:w.shape[1]]
    return w.float()*scale_full.float()

def dequant_checkpoint(w,s,nh,nk,hd,vd,ckpt_tp):
    rows=chunk_rows(nh,nk,hd,vd,ckpt_tp)
    sr=cdiv(rows,BLOCK)
    out=[]
    for c in range(ckpt_tp):
        wc=w[c*rows:(c+1)*rows]
        sc=s[c*sr:(c+1)*sr]
        out.append(dequant_output(wc,sc))
    return torch.cat(out,0)

def rel_l2(a,b):
    return float((a-b).norm()/b.norm().clamp_min(1e-12))

results={"synthetic":{},"real":{},"negative":{}}

torch.manual_seed(12345)
for name,(nh,nk,hd,vd,ckpt_tp) in GEOMS.items():
    rows=chunk_rows(nh,nk,hd,vd,ckpt_tp)
    truth=torch.randn(ckpt_tp*rows,COLS)
    for c in range(ckpt_tp):
        truth[c*rows:(c+1)*rows]*=(1.0+c)
    w,s=manual_quantize_chunks(truth,nh,nk,hd,vd,ckpt_tp)
    entries=[]
    for tp in (1,2,4):
        for rank in range(tp):
            wr,sr=new._mimo26_shard_fp8_qkv_proj(w,s,nh,nk,hd,vd,rank,tp,ckpt_tp=4)
            got=dequant_output(wr,sr)
            exp=truth[owned_indices(nh,nk,hd,vd,ckpt_tp,rank,tp)]
            rel=rel_l2(got,exp)
            ma=float((got-exp).abs().max())
            exact=None
            if tp==ckpt_tp:
                ew=w.chunk(tp,0)[rank]; es=s.chunk(tp,0)[rank]
                exact=bool(torch.equal(wr.view(torch.uint8),ew.view(torch.uint8)) and torch.equal(sr,es))
                assert exact
            assert rel<=TOL,(name,tp,rank,rel)
            entries.append({"tp":tp,"rank":rank,"rel_l2":rel,"max_abs":ma,"exact_chunk":exact})
    results["synthetic"][name]=entries

# Regression-negative: old global interpretation must fail against independent per-chunk truth.
nh,nk,hd,vd,ckpt_tp=GEOMS["swa"]
rows=chunk_rows(nh,nk,hd,vd,ckpt_tp)
# Row-coded deterministic fixture: every exported row has a distinct value
# pattern, so a wrong row permutation cannot hide behind an iid distribution.
rid=torch.arange(ckpt_tp*rows,dtype=torch.float32).unsqueeze(1)
col=torch.linspace(-0.25,0.25,COLS,dtype=torch.float32).unsqueeze(0)
truth=0.125 + rid/2048.0 + col
w,s=manual_quantize_chunks(truth,nh,nk,hd,vd,ckpt_tp)
neg=[]
for rank in (0,1):
    try:
        wr,sr=old._mimo26_shard_fp8_qkv_proj(w,s,nh,nk,hd,vd,rank,2)
        got=dequant_output(wr,sr)
        exp=truth[owned_indices(nh,nk,hd,vd,ckpt_tp,rank,2)]
        rel=rel_l2(got,exp)
        neg.append({"rank":rank,"rel_l2":rel,"raised":False})
    except Exception as e:
        neg.append({"rank":rank,"raised":True,"error":f"{type(e).__name__}: {e}"})
vals=[x.get("rel_l2") for x in neg if not x.get("raised")]
assert all(x.get("raised") or x.get("rel_l2",0)>2*TOL for x in neg),neg
assert any(x.get("raised") or x.get("rel_l2",0)>5*TOL for x in neg),neg
results["negative"]["old_global_swa_tp2"]=neg

# Real checkpoint: choose one full and one SWA fused-QKV tensor.
cfg=json.loads((MODEL/"config.json").read_text())
pattern=cfg["hybrid_layer_pattern"]
found={}
for fn in sorted(MODEL.glob("model_pp0_ep*_shard0.safetensors")):
    with safe_open(fn,framework="pt",device="cpu") as f:
        keys=set(f.keys())
        for k in keys:
            if not k.endswith("self_attn.qkv_proj.weight"): continue
            layer=int(k.split(".layers.")[1].split(".")[0])
            kind="swa" if pattern[layer]==1 else "full"
            sk=k+"_scale_inv"
            if kind not in found and sk in keys:
                found[kind]=(fn,k,sk,layer)
    if len(found)==2: break
assert len(found)==2,found

for kind,(fn,wk,sk,layer) in found.items():
    if kind=="full":
        nh,nk,hd,vd,ckpt_tp=64,4,192,128,4
    else:
        nh,nk,hd,vd,ckpt_tp=64,8,192,128,4
    with safe_open(fn,framework="pt",device="cpu") as f:
        w=f.get_tensor(wk).contiguous(); s=f.get_tensor(sk).contiguous()
    rows=chunk_rows(nh,nk,hd,vd,ckpt_tp)
    assert w.shape[0]==rows*ckpt_tp
    assert s.shape[0]==ckpt_tp*cdiv(rows,BLOCK)
    truth=dequant_checkpoint(w,s,nh,nk,hd,vd,ckpt_tp)
    entries=[]
    for tp in (1,2,4):
        for rank in range(tp):
            wr,sr=new._mimo26_shard_fp8_qkv_proj(w,s,nh,nk,hd,vd,rank,tp,ckpt_tp=4)
            got=dequant_output(wr,sr)
            exp=truth[owned_indices(nh,nk,hd,vd,ckpt_tp,rank,tp)]
            rel=rel_l2(got,exp)
            ma=float((got-exp).abs().max())
            exact=None
            if tp==4:
                ew=w.chunk(4,0)[rank]; es=s.chunk(4,0)[rank]
                exact=bool(torch.equal(wr.view(torch.uint8),ew.view(torch.uint8)) and torch.equal(sr,es))
                assert exact
            assert rel<=TOL,(kind,tp,rank,rel,ma)
            entries.append({"tp":tp,"rank":rank,"rel_l2":rel,"max_abs":ma,"exact_chunk":exact})
    results["real"][kind]={
      "file":fn.name,"weight":wk,"scale":sk,"layer":layer,
      "weight_shape":list(w.shape),"scale_shape":list(s.shape),
      "rows_per_chunk":rows,"scale_rows_per_chunk":cdiv(rows,BLOCK),
      "cases":entries,
    }

out=ROOT/"docs/mimo26/evidence/qkv-upstream-57508/fixture-results.json"
out.write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps(results,indent=2))
print("MIMO26_QKV_57508_FIXTURES_PASS")
