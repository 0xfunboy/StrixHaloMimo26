"""Inventory metadata/tensor descriptors through the pinned upstream GGUF reader."""
from __future__ import annotations
import collections
import json
from pathlib import Path
import sys
from common import atomic,now

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
BASE=Path('/home/funboy/ai-exp/strix-generalist-selection-001')


def main():
    sys.path.insert(0,str(BASE/'qwen-runtime/gguf-py'))
    from gguf import GGUFReader,GGUFValueType
    files=[]
    folder=Path('/home/funboy/models/gguf/qwen38-flash-next-agenticrequant')
    paths=sorted(folder.glob('trunk-q5k-*.gguf'))+[folder/'mtp-Qwen3.8-Flash-Next-Q5_K-frspec-65k.gguf']
    mixed=Path('/home/funboy/models/MiMo-V2.6/mixed-gguf/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF/MQ-IQ2-XXS-XS-Q8-MM-BF16')
    paths+=sorted(mixed.glob('MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-*-of-00004.gguf'))
    for path in paths:
        reader=GGUFReader(path,'r');metadata={};families={};tensors=[]
        for name,field in reader.fields.items():
            if field.types and field.types[0]!=GGUFValueType.ARRAY:
                value=field.contents()
                metadata[name]=value if not isinstance(value,str) or len(value)<20000 else {'string_length':len(value),'stored_in_original_header':True}
            else:metadata[name]={'type':'array','length':len(field.data),'not_expanded':True}
        for t in reader.tensors:
            family='experts' if '_exps' in t.name or 'experts' in t.name else 'attention' if 'attn' in t.name else 'embedding_output' if 'token_embd' in t.name or t.name=='output.weight' else 'other_dense_state'
            families.setdefault(family,collections.Counter())[t.tensor_type.name]+=1
            tensors.append({'name':t.name,'type':t.tensor_type.name,'shape':[int(x) for x in t.shape],'bytes':t.n_bytes,'offset':t.data_offset})
        files.append({'path':str(path),'bytes':path.stat().st_size,'metadata':metadata,'families':{k:dict(v) for k,v in families.items()},'tensors':tensors,'mode':'read-only mmap; tensor payload arrays never accessed'})
        print(path.name,dict((k,dict(v)) for k,v in families.items()),flush=True)
        del reader
    atomic(ROOT/'preflight/gguf-inventory.json',{'status':'PASS','at':now(),'files':files,'no_inference':True,'reader_source_revision':'ba5354d46ca63e8225c28e1331f0f7651723ad05'})

if __name__=='__main__':main()
