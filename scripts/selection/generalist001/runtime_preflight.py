"""Bounded binary option checks and MTP vocabulary-map inspection; no model load."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
from common import atomic,now,sha

ROOT=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
BASE=Path('/home/funboy/ai-exp/strix-generalist-selection-001')


def config_env(profile):
    cfg=json.loads((ROOT/('config-'+profile+'.json')).read_text());env={}
    for s in cfg['rank0']['argv'][1:]:
        if s=='-i':continue
        if '=' not in s:break
        k,v=s.split('=',1);env[k]=v
    return env


def main():
    manifest=json.loads((ROOT/'source-manifest.json').read_text());checks={}
    for profile in ['Q','M','D']:
        spec=manifest['profiles'][profile];env=config_env(profile)
        # --help is parsed before engine construction in the inspected sources.
        cmd=spec['command']+['--help']
        cp=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30)
        (ROOT/'preflight'/('runtime-options-'+profile+'.txt')).write_text(cp.stdout+cp.stderr)
        checks[profile]={'returncode':cp.returncode,'command':cmd,'status':'PASS' if cp.returncode==0 else 'FAIL','binary_sha256':sha(spec['binary']['path']),'no_inference':True}
        print(profile,cp.returncode,(cp.stderr+cp.stdout)[-800:] if cp.returncode else 'options accepted',flush=True)
    sys.path.insert(0,str(BASE/'qwen-runtime/gguf-py'))
    from gguf import GGUFReader
    path=Path('/home/funboy/models/gguf/qwen38-flash-next-agenticrequant/mtp-Qwen3.8-Flash-Next-Q5_K-frspec-65k.gguf')
    reader=GGUFReader(path,'r');maps=[]
    for t in reader.tensors:
        if t.tensor_type.name=='I64':
            ids=t.data.reshape(-1).tolist()
            maps.append({'name':t.name,'count':len(ids),'min':min(ids),'max':max(ids),'unique':len(set(ids))==len(ids),'nonnegative':all(x>=0 for x in ids),'values_sha256':sha_bytes(ids)})
    assert maps and all(x['unique'] and x['nonnegative'] and x['max']<248320 for x in maps),'MTP_VOCAB_MAPPING_INVALID'
    atomic(ROOT/'preflight/runtime-options.json',{'status':'PASS' if all(x['status']=='PASS' for x in checks.values()) else 'FAIL','at':now(),'profiles':checks})
    atomic(ROOT/'preflight/mtp-mapping.json',{'status':'PASS','at':now(),'maps':maps,'scope':'Read only the small I64 remapping tensor; no model inference, output equivalence or sampled-distribution claim.'})
    print('MTP_MAP',maps)


def sha_bytes(ids):
    import hashlib
    return hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest()

if __name__=='__main__':main()
