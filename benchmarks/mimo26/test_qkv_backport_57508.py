from __future__ import annotations
import json
from pathlib import Path
import torch
from safetensors import safe_open

from vllm_patch import _mimo26_shard_fp8_qkv_proj

BLOCK=128
FP8=torch.float8_e4m3fn
FP8_MAX=torch.finfo(FP8).max
CKPT_TP=4
TOL=0.06

def cdiv(a,b): return (a+b-1)//b

def chunk_rows(nh,nk,hd,vd,ckpt_tp=CKPT_TP):
    return nh//ckpt_tp*hd + nk//ckpt_tp*hd + nk//ckpt_tp*vd

def independent_quantize_chunks(truth, nh,nk,hd,vd,ckpt_tp=CKPT_TP):
    """Independent reference export: quantize each [Q_c|K_c|V_c] chunk separately."""
    rpc=chunk_rows(nh,nk,hd,vd,ckpt_tp)
    weights=[]; scales=[]
    for c in range(ckpt_tp):
        rows=truth[c*rpc:(c+1)*rpc]
        q=torch.zeros_like(rows)
        s=torch.empty((cdiv(rpc,BLOCK), cdiv(rows.shape[1],BLOCK)), dtype=torch.float32)
        for r in range(0,rpc,BLOCK):
            for col in range(0,rows.shape[1],BLOCK):
                blk=rows[r:r+BLOCK,col:col+BLOCK]
                scale=blk.abs().max().clamp(min=1e-12)/FP8_MAX
                s[r//BLOCK,col//BLOCK]=scale
                q[r:r+BLOCK,col:col+BLOCK]=blk/scale
        weights.append(q.to(FP8)); scales.append(s)
    return torch.cat(weights,0), torch.cat(scales,0)

def independent_owned_rows(truth,nh,nk,hd,vd,tp_rank,tp_size,ckpt_tp=CKPT_TP):
    rpc=chunk_rows(nh,nk,hd,vd,ckpt_tp)
    qpc=nh//ckpt_tp*hd
    kpc=nk//ckpt_tp*hd
    q_heads=list(range(tp_rank*(nh//tp_size),(tp_rank+1)*(nh//tp_size)))
    if tp_size<=nk:
        kv_heads=list(range(tp_rank*(nk//tp_size),(tp_rank+1)*(nk//tp_size)))
    else:
        kv_heads=[tp_rank//(tp_size//nk)]
    idx=[]
    for h in q_heads:
        c,o=divmod(h,nh//ckpt_tp)
        idx.extend(range(c*rpc+o*hd,c*rpc+(o+1)*hd))
    for h in kv_heads:
        c,o=divmod(h,nk//ckpt_tp)
        start=c*rpc+qpc+o*hd
        idx.extend(range(start,start+hd))
    for h in kv_heads:
        c,o=divmod(h,nk//ckpt_tp)
        start=c*rpc+qpc+kpc+o*vd
        idx.extend(range(start,start+vd))
    return truth[torch.tensor(idx)]

def independent_dequant(weight,scale):
    # Output of the function under test is a normal per-rank block grid.
    rows=weight.shape[0]
    per=scale.repeat_interleave(BLOCK,0).repeat_interleave(BLOCK,1)
    return weight.to(torch.float32)*per[:rows,:weight.shape[1]]

def rel_l2(a,b):
    return float((a-b).norm()/b.norm())

def synthetic():
    torch.manual_seed(1234)
    geoms={
      'full':(64,4,192,128),
      'swa':(64,8,192,128),
    }
    out=[]
    for name,(nh,nk,hd,vd) in geoms.items():
        rpc=chunk_rows(nh,nk,hd,vd)
        truth=torch.randn(CKPT_TP*rpc,128)
        for c in range(CKPT_TP):
            truth[c*rpc:(c+1)*rpc]*=(1.0+c)
        w,s=independent_quantize_chunks(truth,nh,nk,hd,vd)
        for tp in (1,2,4):
            for rank in range(tp):
                wr,sr=_mimo26_shard_fp8_qkv_proj(w,s,nh,nk,hd,vd,rank,tp)
                exp=independent_owned_rows(truth,nh,nk,hd,vd,rank,tp)
                got=independent_dequant(wr,sr)
                e=rel_l2(got,exp)
                exact=None
                if tp==CKPT_TP:
                    ew=w.chunk(CKPT_TP,0)[rank]
                    es=s.chunk(CKPT_TP,0)[rank]
                    exact=bool(torch.equal(wr.view(torch.uint8),ew.view(torch.uint8)) and torch.equal(sr,es))
                    assert exact
                assert e<=TOL,(name,tp,rank,e)
                out.append({'kind':'synthetic','geometry':name,'tp':tp,'rank':rank,'rel_l2':e,'exact_tp4':exact})
    return out

def real_checkpoint():
    root=Path('/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL')
    cfg=json.loads((root/'config.json').read_text())
    pattern=cfg['hybrid_layer_pattern']
    found={}
    for fn in sorted(root.glob('model_pp0_ep*_shard0.safetensors')):
        with safe_open(fn,framework='pt',device='cpu') as f:
            keys=set(f.keys())
            for wk in keys:
                if not wk.endswith('self_attn.qkv_proj.weight'): continue
                layer=int(wk.split('.layers.')[1].split('.')[0])
                kind='swa' if pattern[layer]==1 else 'full'
                sk=wk+'_scale_inv'
                if kind not in found and sk in keys:
                    found[kind]=(fn,wk,sk,layer)
        if len(found)==2: break
    assert len(found)==2

    out=[]
    for kind,(fn,wk,sk,layer) in found.items():
        with safe_open(fn,framework='pt',device='cpu') as f:
            w=f.get_tensor(wk).contiguous(); s=f.get_tensor(sk).contiguous()
        if kind=='swa':
            nh=cfg['swa_num_attention_heads']; nk=cfg['swa_num_key_value_heads']; hd=cfg['swa_head_dim']; vd=cfg['swa_v_head_dim']
        else:
            nh=cfg['num_attention_heads']; nk=cfg['num_key_value_heads']; hd=cfg['head_dim']; vd=cfg['v_head_dim']
        rpc=chunk_rows(nh,nk,hd,vd)
        expected_scale_rows=CKPT_TP*cdiv(rpc,BLOCK)
        assert w.shape[0]==CKPT_TP*rpc,(kind,w.shape,rpc)
        assert s.shape[0]==expected_scale_rows,(kind,s.shape,expected_scale_rows)

        # Independent dequant of the *checkpoint export* using per-chunk scales.
        pieces=[]
        for c in range(CKPT_TP):
            wc=w[c*rpc:(c+1)*rpc]
            sc=s[c*cdiv(rpc,BLOCK):(c+1)*cdiv(rpc,BLOCK)]
            per=sc.repeat_interleave(BLOCK,0).repeat_interleave(BLOCK,1)
            pieces.append(wc.to(torch.float32)*per[:rpc,:wc.shape[1]])
        truth=torch.cat(pieces,0)

        for tp in (1,2,4):
            for rank in range(tp):
                wr,sr=_mimo26_shard_fp8_qkv_proj(w,s,nh,nk,hd,vd,rank,tp)
                exp=independent_owned_rows(truth,nh,nk,hd,vd,rank,tp)
                got=independent_dequant(wr,sr)
                e=rel_l2(got,exp)
                max_abs=float((got-exp).abs().max())
                exact=None
                if tp==CKPT_TP:
                    ew=w.chunk(CKPT_TP,0)[rank]
                    es=s.chunk(CKPT_TP,0)[rank]
                    exact=bool(torch.equal(wr.view(torch.uint8),ew.view(torch.uint8)) and torch.equal(sr,es))
                    assert exact
                assert e<=TOL,(kind,tp,rank,e)
                out.append({'kind':'real','geometry':kind,'layer':layer,'file':fn.name,'weight_shape':list(w.shape),'scale_shape':list(s.shape),'tp':tp,'rank':rank,'rel_l2':e,'max_abs':max_abs,'exact_tp4':exact})
    return out

def negative_global_layout():
    # Full-attention scale arithmetic independently proves per-chunk tiling:
    # 4 * ceil(3392/128) = 108, while ceil(13568/128) = 106.
    # SWA chunks are exactly 29 blocks (3712 rows), so both arithmetic counts
    # happen to be 116; SWA therefore requires the independent row-mapping
    # reference above and cannot be diagnosed from scale-row count alone.
    cases={'full':(13568,108,3392,27),'swa':(14848,116,3712,29)}
    out=[]
    for name,(rows,srows,rpc,srpc) in cases.items():
        global_rows=cdiv(rows,BLOCK)
        assert srows==CKPT_TP*srpc
        distinguishes=(srows!=global_rows)
        if name=='full':
            assert distinguishes
        else:
            assert not distinguishes
        out.append({'geometry':name,'weight_rows':rows,'scale_rows':srows,'global_scale_rows':global_rows,'chunk_rows':rpc,'chunk_scale_rows':srpc,'ckpt_tp':CKPT_TP,'scale_count_distinguishes_layout':distinguishes})
    return out

res={
 'schema':'mimo26-qkv-57508-qualification-v1',
 'source':'vllm PR #57508 / merge 211e252d0b4f8429f9b15fc52bdfed07782c7f70',
 'ckpt_tp':CKPT_TP,
 'synthetic':synthetic(),
 'real':real_checkpoint(),
 'negative_scale_geometry':negative_global_layout(),
 'status':'PASS',
}
print(json.dumps(res,indent=2))
Path('/home/funboy/StrixHaloMimo26/docs/mimo26/evidence/qkv-upstream-57508/local-qualification.json').write_text(json.dumps(res,indent=2)+'\n')
