"""Record the real E1 readiness endpoint mismatch without sending inference."""
from pathlib import Path
import json
import urllib.error
import urllib.request
import sys
ROOT=Path('/home/funboy/StrixHaloMimo26/docs/selection/strix-generalist-selection-001')
sys.path.insert(0,str(ROOT/'sources'))
from common import atomic,now,sha
from window_guards import unit_state

def main():
    out=ROOT/'recovery-D';out.mkdir(exist_ok=True)
    p=out/'setup-evidence.json'
    if p.exists():print(p.read_text());return
    run=Path('/home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-001')
    assert not (run/'requests').exists() and not (run/'raw-results.jsonl').exists()
    u=unit_state('mimo26-gs001-supervisor-d-001.service')
    assert u['InvocationID']=='fc1b2de966c14058a8e629179516d1bb'
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    endpoints={}
    for endpoint in ['/health','/v1/models']:
        try:
            with opener.open('http://127.0.0.1:18433'+endpoint,timeout=5) as response:code=response.status;data=response.read()
        except urllib.error.HTTPError as e:code=e.code;data=e.read()
        endpoints[endpoint]={'http':code,'body':json.loads(data)}
    assert endpoints['/health']['http']==404
    models=endpoints['/v1/models'];assert models['http']==200
    entry=models['body']['data'][0];assert entry['id']=='deepseek-v4.1-flash' and entry['context_length']==16384
    source=Path('/home/funboy/ai-exp/strix-generalist-selection-001/e1-source-a8f4473/ds4_server.c')
    atomic(p,{'status':'SETUP_BLOCKER_CONFIRMED','at':now(),'run_id':run.name,'unit':u,'endpoints':endpoints,
              'source':str(source),'source_sha256':sha(source),'requests_sent':0,
              'cause':'Frozen D adapter polls nonexistent /health although E1 /v1/models is ready. No generated output exists.',
              'correction_authority':'Original mandate section7: one packaging correction before panel inference with new identity/freeze.',
              'scope':'readiness admission only; same model/binary/numerics/requests/sampling/context/limits; old run preserved'},exclusive=True)
    print(p.read_text())

if __name__=='__main__':main()
