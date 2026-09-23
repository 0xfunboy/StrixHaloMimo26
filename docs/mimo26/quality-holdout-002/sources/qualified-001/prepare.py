"""Build CPU tokenized fixtures, then freeze complete source bytes before GPU windows."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from common import atomic,ids_sha,now,read_jsonl,sha
from panel import make_panel,sanity_panel

REPO=Path('/home/funboy/StrixHaloMimo26')
ROOT=REPO/'docs/mimo26/quality-retention-001'
SOURCE=REPO/'scripts/mimo26/quality_retention_001'
WINDOWS=Path('/home/funboy/.local/state/strixhalomimo26/windows')
PEER_ROOT=Path('/home/funboy/.local/state/strixhalomimo26/quality-retention-001/frozen')
VENV=Path('/home/funboy/StrixHaloClusterGLM/.engine/venv')
MODEL=Path('/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL')
BUILD=Path('/home/funboy/.local/build/llama.cpp-mimo26-mixed-pin-gfx1151')
REL=Path('/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6')
BASE_COMMIT='fb432c37f96c4514e763bb49f57614d9696efe79'
A_COMMIT='58367713a6935c0810103378144008df32e3d5db'
A_BINARY_SHA='5898a81b08e919c507e09fb4252265c5ee3b8373cef13edc475cf267415cd8c7'
PATCH_SHA='eeb66fefbf1b63459e5712c031399f2d24d9ac05956c97b4e979ad03b901be72'
VERSION_PINS={'vllm':'0.1.0rc2.dev9+g9255fd9fb9.rocm100','torch':'2.13.0+rocm10.0.0','transformers':'5.16.1'}


def output(args):return subprocess.check_output([str(x) for x in args],text=True).strip()
def jsonl(path,rows):path.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows))


def build():
    assert not (ROOT/'source-SHA256SUMS').exists(),'FROZEN_PREPARATION_CANNOT_BE_REWRITTEN'
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(str(MODEL),trust_remote_code=True,local_files_only=True)
    cases,expected=make_panel();sanity=sanity_panel()
    def render(c):
        rendered=tok.apply_chat_template(c['messages'],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        ids=tok.apply_chat_template(c['messages'],tokenize=True,add_generation_prompt=True,enable_thinking=False)
        if hasattr(ids,'keys'):ids=ids['input_ids']
        if hasattr(ids,'tolist'):ids=ids.tolist()
        if ids and isinstance(ids[0],list):ids=ids[0]
        ids=[int(x) for x in ids]
        assert ids==list(tok.encode(rendered,add_special_tokens=False)),'TEMPLATE_DOUBLE_BOS_MISMATCH'
        assert 0<len(ids)<=2048 and len(ids)+c['output_cap']+32<=4096,'CONTEXT_BUDGET_EXCEEDED'
        return {**c,'rendered_text':rendered,'rendered_text_sha256':hashlib.sha256(rendered.encode()).hexdigest(),
                'input_token_ids':ids,'input_token_ids_sha256':ids_sha(ids),'input_tokens':len(ids),
                'thinking':False,'add_generation_prompt':True,'tokenizer_add_special_tokens':False}
    cases=[render(c) for c in cases];sanity=[render(c) for c in sanity]
    for e,c in zip(expected,cases):
        text=e['reference_code'] if e['kind']=='code' else json.dumps(e['expected'],ensure_ascii=False)
        e['reference_token_count']=len(tok.encode(text,add_special_tokens=False))
        assert e['reference_token_count']+8<=c['output_cap'],'REFERENCE_DOES_NOT_FIT_CAP'
    jsonl(ROOT/'cases.jsonl',cases);jsonl(ROOT/'expected.jsonl',expected);jsonl(ROOT/'sanity.jsonl',sanity)
    atomic(ROOT/'preflight/tokenization.json',{'status':'PASS','created_at':now(),'input_count':len(cases)+len(sanity),
        'case_input_min':min(x['input_tokens'] for x in cases),'case_input_max':max(x['input_tokens'] for x in cases),
        'case_output_cap_sum':sum(x['output_cap'] for x in cases),'reference_tokens_max':max(e['reference_token_count'] for e in expected),
        'tokenizer_sha256':sha(MODEL/'tokenizer.json'),'template_sha256':sha(MODEL/'chat_template.jinja'),
        'template_roundtrip':'rendered text encoded without automatic BOS exactly equals chat-template IDs'})
    print(json.dumps({'status':'PANEL_TOKENIZED_CPU_ONLY','cases':24,'caps_total':16384,'input_max':max(x['input_tokens'] for x in cases)}))


def freeze():
    assert not (ROOT/'source-SHA256SUMS').exists(),'FREEZE_ALREADY_EXISTS_RECONCILE_INSTEAD'
    for arm in ('A-mixed','B-original'):
        p=WINDOWS/('quality-retention-001-'+arm+'-001')
        assert not p.exists(),'EXISTING_WINDOW_REQUIRES_RECONCILIATION'
    tests=json.loads((ROOT/'preflight/cpu-tests-final.json').read_text());assert tests['status']=='PASS'
    subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',BASE_COMMIT,'HEAD'],check=True)
    binary=BUILD/'bin/llama-server';assert sha(binary)==A_BINARY_SHA
    assert output(['git','-C','/home/funboy/.local/src/llama.cpp-mimo26-mixed-pin','rev-parse','HEAD'])==A_COMMIT
    assert sha(REPO/'benchmarks/mimo26/vllm_patch.py')==PATCH_SHA
    versions={k:importlib.metadata.version(k) for k in VERSION_PINS};assert versions==VERSION_PINS
    sources=ROOT/'sources';sources.mkdir()
    for p in sorted(SOURCE.glob('*.py')):shutil.copyfile(p,sources/p.name)
    for f in ('window_runner.py','window_cleanup.py'):
        shutil.copyfile(REPO/'scripts/mimo26'/f,sources/f)
    shutil.copyfile(REPO/'benchmarks/mimo26/vllm_patch.py',sources/'vllm_patch.py')
    external={}
    external_dir=sources/'resident-lifecycle';external_dir.mkdir()
    for f in ('serve-controller.sh','pair.sh','launch-node.sh'):
        p=REL/'runtime/ds41'/f
        shutil.copyfile(p,external_dir/f);external[str(p)]=sha(p)
    shutil.copyfile(Path('/home/funboy/.config/systemd/user/strixhalomimo26-window@.service'),sources/'qualified-window-template.service')
    gguf=Path('/home/funboy/models/MiMo-V2.6/mixed-gguf/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF/MQ-IQ2-XXS-XS-Q8-MM-BF16/MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-00001-of-00004.gguf')
    shards=sorted(gguf.parent.glob('MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-*-of-00004.gguf'));assert len(shards)==4
    A={'runtime_commit':A_COMMIT,'binary':{'path':str(binary),'sha256':A_BINARY_SHA},'port':18342,'load_timeout_s':600,
       'command':[str(binary),'-m',str(gguf),'--device','ROCm0','--split-mode','none','-ngl','all','-c','4096','-b','512','-ub','128','-np','1','--no-cont-batching','-fa','auto','--host','127.0.0.1','--port','18342','--reasoning','off','--metrics'],
       'build_flags':[line for line in (BUILD/'CMakeCache.txt').read_text().splitlines() if re.match(r'(CMAKE_BUILD_TYPE|GGML_HIP:|GGML_HIP_GRAPHS:|GGML_NATIVE:|GGML_RPC:|GGML_VULKAN:|GPU_TARGETS:)',line)],
       'shared_library_hashes':{str(p):sha(p) for p in sorted((BUILD/'bin').glob('*.so'))},
       'shards_stat_only':[{'path':str(p),'size':p.stat().st_size} for p in shards]}
    vllm_binary_root=VENV/'lib/python3.14/site-packages/vllm'
    B={'versions':versions,'patch_sha256':PATCH_SHA,'master_port':29641,
       'binary_hashes':{str(p):sha(p) for p in sorted(vllm_binary_root.glob('*.so'))},'kwargs':dict(
        model=str(MODEL),runner='generate',trust_remote_code=True,language_model_only=True,
        tensor_parallel_size=2,pipeline_parallel_size=1,distributed_executor_backend='external_launcher',
        dtype='bfloat16',max_model_len=4096,max_num_seqs=1,max_num_batched_tokens=512,
        kv_cache_memory_bytes=1073741824,enforce_eager=True,disable_custom_all_reduce=True,
        enable_expert_parallel=False,enable_prefix_caching=False,seed=1,moe_backend='triton_unfused',disable_log_stats=False)}
    runs={}
    for arm,old,work in [('A','A-mixed',7200),('B','B-original',14400)]:
        run_id='quality-retention-001-'+old+'-001';run=WINDOWS/run_id
        previous=json.loads((WINDOWS/('perf-baseline-001-'+old+'-001')/'config.json').read_text())
        shutil.copyfile(WINDOWS/('perf-baseline-001-'+old+'-001')/'config.json',sources/('qualified-base-config-'+arm+'.json'))
        cfg={'schema':'mimo26-quality-window-v1','campaign':'QUALITY-RETENTION-001','arm':arm,'run_id':run_id,
             'real_k2':True,'use_compute_lock':True,'allowed_k2_states':['READY'],'quiesce_timeout_sec':720,
             'worker_runtime_sec':work+120,'worker_stop_sec':90,'work_timeout_sec':work,'restore_timeout_sec':1200,
             'rank_stagger_sec':0 if arm=='A' else 2,'poll_sec':2,'rank0':None,'rank1':None}
        for rank in (0,1):
            if arm=='A' and rank==1:continue
            oldargv=previous['rank'+str(rank)]['argv'];env={}
            for entry in oldargv[1:]:
                if not re.match(r'^[A-Za-z_][A-Za-z_0-9]*=',entry):break
                k,v=entry.split('=',1)
                if not k.startswith('MIMO26_') and k!='PYTHONPATH':env[k]=v
            node_root=ROOT if rank==0 else PEER_ROOT
            env.update(QR_ROOT=str(node_root),QR_RUN_DIR=str(run),PYTHONDONTWRITEBYTECODE='1',
                       PYTHONPATH=str(node_root/'sources'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
            if arm=='B':
                # Keep the already-qualified AMD SMI import path; do not alter the shared venv.
                amd_smi_path=str(VENV/'lib/python3.14/site-packages/_rocm_sdk_core/share/amd_smi')
                env['PYTHONPATH']=str(node_root/'sources')+':'+amd_smi_path
            if arm=='A':command=['/usr/bin/python3',str(node_root/'sources/adapter_a.py')]
            else:command=[str(VENV/'bin/torchrun'),'--nnodes=2','--nproc-per-node=1','--node-rank='+str(rank),
                          '--master-addr=10.55.0.1','--master-port=29641',str(node_root/'sources/adapter_b.py')]
            cfg['rank'+str(rank)]={'unit':f'mimo26-qr001-{arm.lower()}-r{rank}-001',
                                   'argv':['/usr/bin/env']+[k+'='+v for k,v in env.items()]+command}
        atomic(ROOT/('config-'+arm+'.json'),cfg)
        runs[arm]={'run_id':run_id,'run_dir':str(run),'supervisor_unit':f'mimo26-qr001-supervisor-{arm.lower()}-001.service',
                   'supervisor_runtime_s':work+2040,'supervisor_stop_s':1200,'config':'config-'+arm+'.json'}
    cases=read_jsonl(ROOT/'cases.jsonl')
    manifest={'schema':'mimo26-quality-preregistration-v1','campaign':'QUALITY-RETENTION-001','frozen_at':now(),
        'base_commit':BASE_COMMIT,'entry_commit':output(['git','-C',str(REPO),'rev-parse','HEAD']),
        'models':{'A':{'repository':'Baekpica/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF','revision':'b3794b22b6276f8120c340f52639f5eaa354a3fd','variant':'MQ-IQ2-XXS-XS-Q8-MM-BF16'},
                  'B':{'repository':'XiaomiMiMo/MiMo-V2.6-Flash-RL','revision':'5711b268169967567844e1e560e8a3966da959b1','not_full_bf16':True}},
        'runtimes':{'A':A,'B':B},'runs':runs,'arm_order':['A','RESTORE','B','RESTORE'],
        'case_order':[c['case_id'] for c in cases],'output_cap_total_per_arm':16384,'sanity_per_phase':6,
        'sampling':{'temperature':0.0,'seed':1,'ignore_eos':False,'repetition_penalty':1.0,'presence_penalty':0.0,'frequency_penalty':0.0,'thinking':False},
        'input_contract':{'A':'explicit frozen token IDs; runtime tokenizer crosscheck; API does not echo prompt IDs',
                          'B':'same explicit frozen token IDs plus runtime native echo and tokenizer check',
                          'native_output_ids':{'A':'return_tokens=true nonstreaming tokens array','B':'CompletionOutput.token_ids'},
                          'cache':'zero reused input tokens each request; final slot context counter is not reuse'},
        'timeout_contract':{'A_work_s':7200,'B_work_s':14400,'request_s':'per case frozen in cases.jsonl; alarm for B, socket timeout and elapsed check for A',
            'B_budget_basis':'16384 cap tokens / conservative planning 2 tok/s, plus per-case prompt allowance, load, 12 sanity and >1h margin; not a throughput claim',
            'restore_s':1200,'supervisor':'unchanged qualified window_runner/window_cleanup byte copies; new per-campaign transient unit with finite enlarged bounds'},
        'sandbox':{'image_id':'a58caff183f8eb10c84fce3d3eb8496e684411369848a77bfcf0af9074cc16c4','network':'none','host_mounts':[],
                   'uid':65534,'memory_bytes':268435456,'pids':32,'cpu_seconds':3,'wall_timeout_s':15,'root_read_only':True,'capabilities':[]},
        'external_lifecycle_hashes':external,'restore':{'controller':str(REL/'runtime/ds41/serve-controller.sh'),
                   'preset':'dspark-k2-gfx1151','release_id':'5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513'},
        'tokenizer_files':{str(MODEL/f):sha(MODEL/f) for f in ('tokenizer.json','tokenizer_config.json','chat_template.jinja','config.json','generation_config.json')},
        'peer_root':str(PEER_ROOT),'cpu_tests':{'path':'preflight/cpu-tests-final.json','sha256':sha(ROOT/'preflight/cpu-tests-final.json')},
        'freeze_role':'PREREGISTRATION_BEFORE_ANY_QUALITY_GPU_LOAD','historical_performance':'TERMINAL_PARTIAL_ENGINE_DECODE_ONLY_UNCHANGED',
        'evaluation':'Independent frozen specifications/tests; original B is not ground truth; full 24-case denominator'}
    atomic(ROOT/'source-manifest.json',manifest)
    files=[ROOT/f for f in ('PROTOCOL.md','cases.jsonl','expected.jsonl','sanity.jsonl','source-manifest.json','config-A.json','config-B.json')]
    files+=list(sources.rglob('*'))
    files+=[ROOT/'preflight/cpu-tests-final.json',ROOT/'preflight/tokenization.json',ROOT/'preflight/cpu-prepare-command.json',ROOT/'preflight/supervisor-property-probe.json']
    if (ROOT/'MANDATE.md').exists():files.append(ROOT/'MANDATE.md')
    files=sorted(p for p in files if p.is_file())
    (ROOT/'source-SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(ROOT))+'\n' for p in files))
    print(json.dumps({'status':'SOURCES_FROZEN','files':len(files),'index_sha256':sha(ROOT/'source-SHA256SUMS'),'runs':runs}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','freeze']);a=p.parse_args()
    (build if a.action=='build' else freeze)()
