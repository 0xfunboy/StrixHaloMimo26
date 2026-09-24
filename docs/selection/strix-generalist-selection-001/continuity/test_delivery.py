"""Check metadata reconciliation only; frozen semantic validators are not changed."""
from pathlib import Path
import copy
import json
import sys
import evaluate_continuity as delivery

ROOT=delivery.ROOT
sys.path.insert(0,str(ROOT/'sources'))
import validate
from common import sha


def main():
    original_binding=delivery.BASE_LOAD_PROFILE
    old_verify=delivery.verify_addendum
    manifest={'runs':{'Q':{'config':'config-Q.json'},'M':{'config':'config-M.json'}}}
    frozen_before=copy.deepcopy(manifest)
    actual=ROOT/'sources/adapter_llama_continuity_v1.py'
    checks=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    try:
        delivery.verify_addendum=lambda r:{'addendum_index_sha256':'test-only'}
        for name,valid,other in [('declared adapter',True,[]),('unknown actual adapter',False,[]),('other audit issue',True,['native unrelated problem'])]:
            actual_item={'path':str(actual.resolve()),'sha256':sha(actual) if valid else 'invalid'}
            meta={'load':{'status':'PASS','source_freeze':{'loaded_modules':{'__main__':actual_item}}},
                  'issues':['runtime frozen import mismatch:__main__']+other,
                  'sanity':{'preflight':{'status':'PASS'},'postflight':{'status':'PASS'}}}
            def fake(root,m,p):
                check(name+' effective config',m['runs']['Q']['config']=='continuity/config-Q.json')
                return {'unchanged':'values'},copy.deepcopy(meta),[{'unchanged':'native record'}]
            delivery.BASE_LOAD_PROFILE=fake
            values,got,records=delivery.effective_load_profile(ROOT,manifest,'Q')
            check(name+' records retained',values=={'unchanged':'values'} and records==[{'unchanged':'native record'}])
            check(name+' verdict',got['runtime_qualification']==('PASS' if valid and not other else 'NOT_QUALIFIED_OR_INCOMPLETE'))
            if other:check('unrelated errors retained',other[0] in got['issues'])
        delivery.BASE_LOAD_PROFILE=lambda root,m,p:({'original':'values'},{'original':'meta'},[{'original':'raw'}])
        check('M unchanged',delivery.effective_load_profile(ROOT,manifest,'M')==({'original':'values'},{'original':'meta'},[{'original':'raw'}]))
        check('base manifest unchanged',manifest==frozen_before)
        check('semantic scorer identity unchanged',delivery.original.verdict is validate.verdict)
    finally:
        delivery.BASE_LOAD_PROFILE=original_binding;delivery.verify_addendum=old_verify
    result={'status':'PASS','checks':checks,'scoring_changes':0,'new_inference_calls':0,'kind':'metadata-only synthetic tests'}
    (ROOT/'continuity/delivery-cpu-tests.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
