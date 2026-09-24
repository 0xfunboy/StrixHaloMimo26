"""CPU-only render/tokenization and preregistered request plan construction."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
from common import atomic,ids_sha,sha,now
import panel
from test_cpu import reference

REPO=Path('/home/funboy/StrixHaloMimo26')
ROOT=REPO/'docs/selection/strix-generalist-selection-001'
VENV=Path('/home/funboy/StrixHaloClusterGLM/.engine/venv')
E1=Path('/home/funboy/.local/share/haloclu-ds41/releases/ds4-speed-001-engram1')
DMODEL=Path('/home/funboy/models/ds41/ds4-v41-q2/DeepSeek-V4.1-Flash-Q2.gguf')
MROOT=Path('/home/funboy/models/MiMo-V2.6/official/MiMo-V2.6-Flash-RL')
SYSTEM='You are a helpful assistant'


def deepseek_render(content,thinking):
    effort='Reasoning Effort: 100 (range 1-100, the higher the value, the more thorough the reasoning)\n\n' if thinking else ''
    return '<｜begin▁of▁sentence｜><｜System｜>'+effort+SYSTEM+'<｜User｜>'+content+'<｜Assistant｜>'+('<think>' if thinking else '</think>')


def native_d_tokens(content,thinking,root):
    # The existing binary returns here after metadata/vocabulary access, before
    # engine initialization. No GPU workload or model inference is started.
    inputpath=root/'preflight/d-native-tokenizer-input.txt'
    inputpath.write_text(content)
    cmd=[str(E1/'ds4'),'--cpu','-m',str(DMODEL),'--dump-tokens','--raw-prompt','--prompt-file',str(inputpath),'-c','16384','--think-max' if thinking else '--nothink']
    cp=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
    if cp.returncode:raise RuntimeError('D_NATIVE_TOKENIZER:'+cp.stderr[-1500:])
    return json.loads(cp.stdout.splitlines()[0])


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);args=p.parse_args();root=args.root.resolve()
    if (root/'source-SHA256SUMS').exists():raise RuntimeError('FROZEN_PREPARATION_CANNOT_BE_REBUILT')
    from transformers import AutoTokenizer
    tok_m=AutoTokenizer.from_pretrained(str(MROOT),local_files_only=True,trust_remote_code=True)
    tok_q=AutoTokenizer.from_pretrained(str(root/'upstream/qwen-official'),local_files_only=True,trust_remote_code=True)
    tokenizers={'Q':tok_q,'M':tok_m,'O':tok_m}
    rows=panel.cases();public=[];oracles=[]
    for row in rows:
        public.append({k:v for k,v in row.items() if k!='oracle'})
        oracles.append({'case_id':row['case_id'],**row['oracle']})
    (root/'cases.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in public))
    (root/'expected.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in oracles))
    intro,sections=panel.engine_document();bench={}
    for label,target in [('2K',2048),('8K',8192)]:
        text=intro
        for section in sections:
            candidate=text+section
            count=len(tok_m.encode(candidate,add_special_tokens=False))
            if count>target and abs(len(tok_m.encode(text,add_special_tokens=False))-target)<abs(count-target):break
            text=candidate
            if count>=target:break
        bench[label]={'case_id':'ENGINE-'+label,'content':text,'output_cap':128,'target_tokens_approx':target}
    (root/'engine-documents.json').write_text(json.dumps(bench,indent=2,ensure_ascii=False)+'\n')
    mtp=panel.mtp_cases();(root/'mtp-cases.json').write_text(json.dumps(mtp,indent=2)+'\n')
    plans={};token_checks={};delimiters={}
    for profile in ['Q','M','D','O']:
        records=[];checks=[];cache={}
        def render(content,thinking):
            key=(content,thinking)
            if key in cache:return cache[key]
            messages=[{'role':'system','content':SYSTEM},{'role':'user','content':content}]
            if profile=='D':
                text=deepseek_render(content,thinking)
                ids=native_d_tokens(text,thinking,root)
            else:
                tk=tokenizers[profile]
                text=tk.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=thinking,reasoning_effort='xhigh')
                ids=list(tk.encode(text,add_special_tokens=False))
                direct=tk.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=thinking,reasoning_effort='xhigh')
                if hasattr(direct,'keys'):direct=direct['input_ids']
                if hasattr(direct,'tolist'):direct=direct.tolist()
                if direct and isinstance(direct[0],list):direct=direct[0]
                assert list(direct)==ids,'DOUBLE_TEMPLATE_OR_ID_DIFFERENCE'
            cache[key]=(messages,text,[int(i) for i in ids]);return cache[key]
        for phase,items in [('preflight',panel.sanity()),('panel',rows),('warmup',[bench['2K'],bench['8K']]),('benchmark',[bench[x] for x in ['2K','8K','2K','8K','2K','8K']]),('postflight',panel.sanity())]:
            counts={}
            for item in items:
                thinking=phase not in ('benchmark','warmup')
                messages,text,ids=render(item['content'],thinking)
                counts[item['case_id']]=counts.get(item['case_id'],0)+1
                request_key=item['case_id']+(('-r'+str(counts[item['case_id']])) if phase=='benchmark' else '')
                cap=item['output_cap']
                assert len(ids)+cap+256<=16384,(profile,item['case_id'],len(ids))
                if phase=='panel':assert len(ids)<=3072,(profile,item['case_id'],len(ids))
                sampling={'temperature':1.0 if thinking else 0.0,'top_p':.95 if thinking else 1.0,'top_k':20 if profile=='Q' and thinking else 0,'min_p':0.0,'repetition_penalty':1.0,'presence_penalty':0.0,'frequency_penalty':0.0,'seed':101,'ignore_eos':False}
                record={'case_id':item['case_id'],'request_key':request_key,'phase':phase,'profile':profile,'family':item.get('family','SANITY' if phase in ('preflight','postflight') else 'ENGINE'),
                        'sanity_name':item.get('name'),'messages':messages,'rendered_text':text,'input_token_ids':ids,'input_ids_sha256':ids_sha(ids),
                        'input_tokens':len(ids),'output_cap':cap,'thinking':thinking,'sampling':sampling,
                        'timeout_s':int(cap/2+300) if phase=='panel' else 1200 if phase in ('preflight','postflight') else 900,
                        'measured':phase=='benchmark','input_bytes':len(text.encode())}
                records.append(record)
                checks.append({'phase':phase,'case_id':item['case_id'],'request_key':request_key,'input_tokens':len(ids),'input_bytes':len(text.encode()),'cap':cap,'thinking':thinking,'roundtrip':'NATIVE_METADATA_ONLY' if profile=='D' else 'TEMPLATE_ID_EQUALS_RENDER_ENCODE'})
        # Crosscheck ON/OFF differs before any runtime load.
        for row in rows:
            _,off,oid=render(row['content'],False);_,on,iid=render(row['content'],True)
            assert off!=on and oid!=iid
        if profile=='Q':
            mr=[]
            for item in mtp:
                msgs,text,ids=render(item['content'],False)
                assert len(ids)+item['output_cap']+256<=16384
                for spec in [False,True]:
                    mr.append({'case_id':item['case_id'],'request_key':item['case_id']+('-ON' if spec else '-OFF'),'phase':'mtp_equivalence','profile':'Q','messages':msgs,'rendered_text':text,'input_token_ids':ids,'input_ids_sha256':ids_sha(ids),'input_tokens':len(ids),'output_cap':256,'thinking':False,'speculation':spec,'sampling':{'temperature':0.0,'top_p':1.0,'top_k':0,'min_p':0.0,'repetition_penalty':1.0,'presence_penalty':0.0,'frequency_penalty':0.0,'seed':101,'ignore_eos':False},'timeout_s':1200,'measured':False,'input_bytes':len(text.encode())})
            atomic(root/'mtp-request-plan.json',mr)
            assert any(x['input_tokens']>2048 for x in mr),'MTP_NO_BEYOND_MICROBATCH_CASE'
        plans[profile]=records;token_checks[profile]=checks
        (root/('requests-'+profile+'.jsonl')).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in records))
        print(profile,'panel_max',max(x['input_tokens'] for x in records if x['phase']=='panel'),'requests',len(records),flush=True)
    for m,o in zip(plans['M'],plans['O']):assert m['input_token_ids']==o['input_token_ids'] and m['rendered_text']==o['rendered_text']
    for name,t in [('Q',tok_q),('M',tok_m)]:
        delimiters[name]={'open':list(t.encode('<think>',add_special_tokens=False)),'close':list(t.encode('</think>',add_special_tokens=False))}
    reference_counts={}
    for row in rows:
        final=json.dumps(reference(row['oracle']),ensure_ascii=False)
        reference_counts[row['case_id']]={k:len(t.encode(final,add_special_tokens=False)) for k,t in [('Q',tok_q),('M',tok_m)]}
        assert max(reference_counts[row['case_id']].values())<row['output_cap']
    atomic(root/'preflight/tokenization.json',{'status':'PASS','at':now(),'profiles':token_checks,'delimiters':delimiters,'reference_tokens':reference_counts,'mimo_pair_identical':True,'context':16384,'panel_cap_total':73728,'native_D_tokenizer':'existing E1 --cpu --dump-tokens metadata path, no inference'})
    print(json.dumps({'status':'INPUT_PREPARATION_PASS','profiles':list(plans),'cases':12,'requests_per_profile':32}))

if __name__=='__main__':main()
