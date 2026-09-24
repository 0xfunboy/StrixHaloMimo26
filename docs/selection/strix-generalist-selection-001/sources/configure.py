"""Create isolated candidate launch configurations before source freeze."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
from common import atomic,now,sha

REPO=Path('/home/funboy/StrixHaloMimo26');ROOT=REPO/'docs/selection/strix-generalist-selection-001'
BASE=Path('/home/funboy/ai-exp/strix-generalist-selection-001')
WINDOWS=Path('/home/funboy/.local/state/strixhalomimo26/windows')
PEER=Path('/home/funboy/.local/state/strixhalomimo26/strix-generalist-selection-001/frozen')
VENV=Path('/home/funboy/StrixHaloClusterGLM/.engine/venv')
MROOT=Path('/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL')
E1=Path('/home/funboy/.local/share/haloclu-ds41/releases/ds4-speed-001-engram1')
REL=Path('/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6')


def old_env(config):
    env={}
    for x in config['rank0']['argv'][1:]:
        if '=' not in x:break
        k,v=x.split('=',1)
        if not k.startswith('MIMO26_') and k!='PYTHONPATH':env[k]=v
    return env


def main():
    if (ROOT/'source-SHA256SUMS').exists():raise RuntimeError('CONFIGURATION_ALREADY_FROZEN')
    oldroot=REPO/'docs/mimo26/quality-holdout-002'
    prior=json.loads((oldroot/'source-manifest.json').read_text())
    a=prior['runtimes']['A'];b=prior['runtimes']['B']
    ca=json.loads((oldroot/'config-A.json').read_text());cb=json.loads((oldroot/'config-B.json').read_text())
    env_m=old_env(ca);env_o=old_env(cb)
    tok=ROOT/'tokenizers';(tok/'mimo').mkdir(parents=True,exist_ok=True);(tok/'qwen').mkdir(exist_ok=True)
    for name in ['tokenizer.json','tokenizer_config.json','chat_template.jinja','config.json','generation_config.json']:
        for source,dest in [(MROOT/name,tok/'mimo'/name),(ROOT/'upstream/qwen-official'/name,tok/'qwen'/name)]:
            if dest.exists():assert dest.read_bytes()==source.read_bytes()
            else:shutil.copyfile(source,dest)
    profiles={}
    qbin=BASE/'qwen-build/bin/llama-server'
    qlibs={str(p):sha(p) for p in (BASE/'qwen-build/bin').glob('*.so*') if p.is_file() and not p.is_symlink()}
    qmodel=Path('/home/funboy/models/gguf/qwen38-flash-next-agenticrequant/trunk-q5k-00001-of-00003.gguf')
    profiles['Q']={'status':'ADMITTED_PENDING_ASSET_GATE','name':'Qwen3.8-Flash-Next AgenticRequant Q5K','nodes':1,
        'repository':'drluoto/Qwen3.8-Flash-Next-AgenticRequant-Q5K-GGUF','weight_revision':'d69cf601fafd166c9d39caa0ab41fd1ab51a0763',
        'runtime_revision':'ba5354d46ca63e8225c28e1331f0f7651723ad05','runtime_source':str(BASE/'qwen-runtime'),'backend':'Vulkan/RADV gfx1151',
        'binary':{'path':str(qbin),'sha256':sha(qbin)},'library_hashes':qlibs,'model_path':str(qmodel),
        'tokenizer_json':'tokenizers/qwen/tokenizer.json','think_open_id':248068,'think_close_id':248069,'eos_ids':[248046,248044],
        'thinking_prefix_open':True,'reasoning_control':'Frozen official xhigh template; native input IDs, no reasoning budget injection',
        'port':18431,'load_timeout_s':900,
        'command':[str(qbin),'-m',str(qmodel),'-ngl','all','--device','Vulkan0','--split-mode','none','-c','16384','-b','2048','-ub','2048','-np','1','--no-cont-batching','-fa','on','-ctk','f16','-ctv','f16','-lm','dio','--host','127.0.0.1','--port','18431','--spec-type','none','--reasoning','on','--reasoning-effort','xhigh','--reasoning-budget','-1','--metrics']}
    mbin=Path(a['binary_path']) if 'binary_path' in a else Path('/home/funboy/.local/build/llama.cpp-mimo26-mixed-pin-gfx1151/bin/llama-server')
    model=next(x.split('=',1)[1] for x in ca['rank0']['argv'] if x.startswith('MIMO26_GGUF_FIRST_SHARD=')) if any(x.startswith('MIMO26_GGUF_FIRST_SHARD=') for x in ca['rank0']['argv']) else '/home/funboy/models/MiMo-V2.6/mixed-gguf/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF/MQ-IQ2-XXS-XS-Q8-MM-BF16/MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-00001-of-00004.gguf'
    profiles['M']={'status':'ADMITTED','name':'MiMo-V2.6 Flash RL mixed IQ2/Q8','nodes':1,'repository':'Baekpica/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF',
        'weight_revision':'b3794b22b6276f8120c340f52639f5eaa354a3fd','runtime_revision':'58367713a6935c0810103378144008df32e3d5db','backend':'HIP gfx1151',
        'binary':{'path':str(mbin),'sha256':sha(mbin)},'library_hashes':{str(p):sha(p) for p in mbin.parent.glob('*.so*') if p.is_file() and not p.is_symlink()},
        'model_path':model,'tokenizer_json':'tokenizers/mimo/tokenizer.json','think_open_id':151667,'think_close_id':151668,'eos_ids':[151643,151645,151672],
        'thinking_prefix_open':False,'reasoning_control':'Frozen Xiaomi enable_thinking=True rendering; generated native control tokens distinguish reasoning from final',
        'port':18432,'load_timeout_s':900,
        'command':[str(mbin),'-m',model,'--device','ROCm0','--split-mode','none','-ngl','all','-c','16384','-b','512','-ub','128','-np','1','--no-cont-batching','-fa','auto','-ctk','f16','-ctv','f16','--host','127.0.0.1','--port','18432','--reasoning','on','--metrics']}
    dmodel=Path('/home/funboy/models/ds41/ds4-v41-q2/DeepSeek-V4.1-Flash-Q2.gguf');drun=WINDOWS/'generalist-selection-001-D-001'
    profiles['D']={'status':'ADMITTED','name':'DeepSeek-V4.1-Flash Q2 E1 Engram concurrent','nodes':2,'backend':'native E1 ROCm TCP TP2',
        'runtime_revision':'a8f44737ecc6bbd406d796d1e402b312f00d1564','source_archive':str(BASE/'e1-source-a8f4473.tar'),
        'binary':{'path':str(E1/'ds4-server'),'sha256':sha(E1/'ds4-server')},'worker_binary':{'path':str(E1/'ds4'),'sha256':sha(E1/'ds4')},
        'model_path':str(dmodel),'model_size':dmodel.stat().st_size,'model_format':'existing native Q2 experts and dense types; separate Engram component unchanged',
        'api_model':'deepseek-v4.1-flash','port':18433,'tp_port':9917,'load_timeout_s':1200,'peer_root':str(PEER),'peer_unit':'mimo26-gs001-d-r1-001',
        'reasoning_control':'API reasoning_effort=max maps to native DeepSeek-V4.1 Reasoning Effort: 100, verified on the existing binary CPU tokenizer; explicit sampling overrides defaults',
        'output_ids':'NOT_EXPOSED; native completion count retained; reasoning/final token split null, native strings retained',
        'command':[str(E1/'ds4-server'),'--rocm','-m',str(dmodel),'--ctx','16384','--tensor-parallel','--role','coordinator','--listen','10.55.0.1','9917','--transport','tcp','--batched-session','1','--host','127.0.0.1','--port','18433','--trace',str(drun/'server-trace.log')],
        'worker_command':[str(E1/'ds4'),'--rocm','-m',str(dmodel),'--ctx','16384','--tensor-parallel','--role','worker','--coordinator','10.55.0.1','9917','--transport','tcp']}
    kwargs=dict(model=str(MROOT),runner='generate',trust_remote_code=True,language_model_only=True,tensor_parallel_size=2,pipeline_parallel_size=1,
        distributed_executor_backend='external_launcher',dtype='bfloat16',max_model_len=16384,max_num_seqs=1,max_num_batched_tokens=512,
        kv_cache_memory_bytes=4294967296,enforce_eager=True,disable_custom_all_reduce=True,enable_expert_parallel=False,enable_prefix_caching=False,
        seed=101,moe_backend='triton_unfused',disable_log_stats=False)
    binary_hashes={str(p):sha(p) for p in (VENV/'lib/python3.14/site-packages/vllm').glob('*.so')}
    profiles['O']={'status':'ADMITTED','name':'MiMo-V2.6 Flash RL original FP8/MXFP4','nodes':2,'repository':'XiaomiMiMo/MiMo-V2.6-Flash-RL',
        'weight_revision':'5711b268169967567844e1e560e8a3966da959b1','backend':'vLLM ROCm TP2/PP1 eager triton_unfused',
        'versions':{'vllm':'0.1.0rc2.dev9+g9255fd9fb9.rocm100','torch':'2.13.0+rocm10.0.0','transformers':'5.16.1'},
        'binary_hashes':binary_hashes,'patch_sha256':'eeb66fefbf1b63459e5712c031399f2d24d9ac05956c97b4e979ad03b901be72',
        'tokenizer_json':'tokenizers/mimo/tokenizer.json','think_open_id':151667,'think_close_id':151668,'eos_ids':[151643,151645,151672],
        'thinking_prefix_open':False,'kwargs':kwargs,'minimum_memavailable_bytes':8*2**30,'tp_port':29643,
        'reasoning_control':profiles['M']['reasoning_control'],'KV_gate':'Explicit 4GiB/rank; runtime context/block-capacity initialization must succeed; no fallback resize'}
    for profile in ['Q','M']:
        profiles[profile]['minimum_memavailable_bytes']=8*2**30
    runs={}
    for profile in ['Q','M','D','O']:
        run_id='generalist-selection-001-'+profile+'-001';run=WINDOWS/run_id
        config={'schema':'strix-generalist-window-v1','campaign':'STRIX-GENERALIST-SELECTION-001','campaign_root':str(ROOT),'profile':profile,'run_id':run_id,
            'real_k2':True,'use_compute_lock':True,'allowed_k2_states':['READY'],'quiesce_timeout_sec':720,'worker_runtime_sec':55120,'worker_stop_sec':120,
            'work_timeout_sec':55000,'restore_timeout_sec':1200,'rank_stagger_sec':2 if profile=='O' else 0,'poll_sec':2,
            'reserved_ports':[profiles[profile][k] for k in ['port','tp_port'] if k in profiles[profile]],'rank0':None,'rank1':None}
        for rank in [0,1]:
            if rank==1 and profile not in ('D','O'):continue
            where=ROOT if rank==0 else PEER
            if profile=='Q':env={'PATH':str(VENV/'bin')+':/usr/bin:/bin','LD_LIBRARY_PATH':str(BASE/'qwen-build/bin')+':/usr/lib/x86_64-linux-gnu'}
            elif profile=='M':env=dict(env_m)
            else:env=dict(env_o)
            for key in list(env):
                if key.startswith(('MIMO26_','QR_','GS_')):del env[key]
            env.update(PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',
                       GS_ROOT=str(where),GS_RUN_DIR=str(run),GS_PROFILE=profile,
                       PYTHONPATH=str(where/'sources')+':'+str(VENV/'lib/python3.14/site-packages/_rocm_sdk_core/share/amd_smi'))
            if profile=='D':
                env.update(OMP_NUM_THREADS='1',DS4_TP_GATE_TIMEOUT_MS='5000')
                # The old E1 launcher inherits no experimental DS4 overrides.
                for key in list(env):
                    if key.startswith('VLLM_') or key.startswith('NCCL_') or key.startswith('GLOO_'):del env[key]
                command=profiles['D']['worker_command'] if rank else [str(VENV/'bin/python'),str(where/'sources/adapter_ds41.py')]
            elif profile=='O':
                env['VLLM_HOST_IP']='10.55.0.1' if rank==0 else '10.55.0.2'
                command=[str(VENV/'bin/torchrun'),'--nnodes=2','--nproc-per-node=1','--node-rank='+str(rank),'--master-addr=10.55.0.1','--master-port=29643',str(where/'sources/adapter_original.py')]
            else:command=[str(VENV/'bin/python'),str(where/'sources/adapter_llama.py')]
            env.update(HOME='/home/funboy',USER='funboy',LOGNAME='funboy',XDG_RUNTIME_DIR='/run/user/1000',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus',LANG='C.UTF-8')
            config['rank'+str(rank)]={'unit':'mimo26-gs001-'+profile.lower()+'-r'+str(rank)+'-001','argv':['/usr/bin/env','-i']+[k+'='+v for k,v in env.items()]+command}
        atomic(ROOT/('config-'+profile+'.json'),config)
        runs[profile]={'run_id':run_id,'run_dir':str(run),'config':'config-'+profile+'.json','supervisor_unit':'mimo26-gs001-supervisor-'+profile.lower()+'-001.service','supervisor_runtime_s':57040,'supervisor_stop_s':1350}
    lifecycle={str(REL/'runtime/ds41'/f):sha(REL/'runtime/ds41'/f) for f in ['serve-controller.sh','pair.sh','launch-node.sh']}
    manifest={'schema':'strix-generalist-source-manifest-v1','campaign':'STRIX-GENERALIST-SELECTION-001','status':'DRAFT_NOT_FROZEN',
        'base_commit':'e6a814336e6f37e88b1cd3a5fab23fc5b299635d','created_at':now(),'profiles':profiles,'runs':runs,'order':['Q','M','D','O'],
        'context':16384,'case_order':[json.loads(x)['case_id'] for x in (ROOT/'cases.jsonl').read_text().splitlines()],
        'panel_output_cap_per_profile':73728,'sanity_output_cap_per_phase':6656,'sanity_per_phase':6,'benchmark_measured_per_profile':6,'warmups_per_profile':2,
        'work_timeout_budget':{'seconds':55000,'basis':'(73728 panel + 13312 sanity + 1024 engine)/2 tok/s + load, request-prefill allowance and >10% margin. 3.417 historical O used only as conservative planning context, not a new result.'},
        'peer_root':str(PEER),'resident_lifecycle_hashes':lifecycle,'restore':{'controller':str(REL/'runtime/ds41/serve-controller.sh'),'release':str(REL),'preset':'dspark-k2-gfx1151','release_id':'5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513'},
        'mtp':{'status':'BLOCKED_STATIC_CONTROL_CONTRACT','reason':'Pinned server-schema.cpp disables per-request speculative.n_max under #if 0; speculative type is global and POST /props exposes no options. A payload pretending to toggle OFF would be ignored. No additional source patch, extra reload or hidden baseline is authorized.',
               'target_unaffected':True,'sidecar_revision':'ac875a98457a8effe8fb83de8f3701421f507a24','sidecar_filename':'mtp-Qwen3.8-Flash-Next-Q5_K-frspec-65k.gguf','additional_loads':0},
        'interpretation':'Complete operating profiles, independent oracles, one sampled generation per task. No inference about stochastic variance, general equivalence or causal effect of thinking/quantization.'}
    atomic(ROOT/'source-manifest.json',manifest)
    print(json.dumps({'status':'CONFIGURATIONS_DRAFTED','profiles':list(profiles),'context':16384,'work_timeout_s':55000,'mtp':manifest['mtp']['status']}))

if __name__=='__main__':main()
