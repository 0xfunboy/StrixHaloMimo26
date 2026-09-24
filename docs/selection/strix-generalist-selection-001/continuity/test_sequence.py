"""Model-free orchestration tests; all launch, unit and resident actions are fakes."""
from pathlib import Path
import contextlib
import io
import json
import subprocess
import tempfile
import types
import continue_sequence as seq


def case(mode):
    with tempfile.TemporaryDirectory(prefix='gs001-sequence-cpu-') as td:
        r=Path(td);(r/'continuity').mkdir();(r/'sources').mkdir();runs={}
        for p in ['Q','M','D','O','T']:runs[p]={'run_id':'test-'+p,'run_dir':str(r/('run-'+p)),'supervisor_unit':'test-'+p}
        (r/'source-manifest.json').write_text(json.dumps({'runs':{k:v for k,v in runs.items() if k!='T'},'restore':{'release_id':'saved'}}))
        (r/'continuity/addendum.json').write_text(json.dumps({'mtp_run':runs['T']}))
        q=Path(runs['Q']['run_dir']);q.mkdir()
        qresult={'run_completion':'FAIL' if mode=='semantic_fault' else 'PASS','cleanup':{'status':'FAIL' if mode=='restore_fault' else 'PASS'}}
        (q/'result.json').write_text(json.dumps(qresult))
        if mode!='no_off':
            (q/'mtp-off').mkdir();(q/'mtp-off/summary.json').write_text(json.dumps({'status':'COMPLETE','records':12}))
        calls=[];busy=[mode=='initially_busy']
        old=(seq.ROOT,seq.verify_addendum,seq.unit_state,seq.controller_status,seq.subprocess.run,seq.subprocess.check_output,seq.time.sleep)
        seq.ROOT=r;seq.verify_addendum=lambda root:{'status':'FAKE'}
        def unit(name):
            if name=='test-Q' and busy[0]:busy[0]=False;return {'ActiveState':'active','MainPID':'11'}
            return {'ActiveState':'inactive','MainPID':'0'}
        seq.unit_state=unit;seq.controller_status=lambda:{'state':'READY','release_id':'saved'}
        seq.subprocess.check_output=lambda *a,**k:'01-EVO-X3\n';seq.time.sleep=lambda x:None
        def launch(argv,**kwargs):
            p=argv[-1];calls.append(p)
            if mode=='timeout':raise subprocess.TimeoutExpired(argv,60)
            d=Path(runs[p]['run_dir']);d.mkdir()
            (d/'result.json').write_text(json.dumps({'run_completion':'PASS','cleanup':{'status':'PASS'}}))
            return types.SimpleNamespace(returncode=0,stdout='fake dispatch',stderr='')
        seq.subprocess.run=launch
        try:
            with contextlib.redirect_stdout(io.StringIO()):rc=seq.main()
            result=json.loads((r/'continuity/sequence.json').read_text())
        finally:
            seq.ROOT,seq.verify_addendum,seq.unit_state,seq.controller_status,seq.subprocess.run,seq.subprocess.check_output,seq.time.sleep=old
        return rc,calls,result['status']


def main():
    cases={'normal':(0,['M','D','O','T'],'AUTHORIZED_WINDOWS_TERMINAL'),
           'initially_busy':(0,['M','D','O','T'],'AUTHORIZED_WINDOWS_TERMINAL'),
           'semantic_fault':(6,[],'BLOCKED_PROFILE_REQUIRES_CAUSAL_CLASSIFICATION'),
           'restore_fault':(4,[],'BLOCKED_RESTORE'),
           'timeout':(2,['M'],'BLOCKED_DISPATCH_TIMEOUT_RECONCILE_ONLY'),
           'no_off':(0,['M','D','O'],'AUTHORIZED_WINDOWS_TERMINAL')}
    results={}
    for mode,expected in cases.items():
        got=case(mode)
        if got!=expected:raise AssertionError((mode,expected,got))
        results[mode]={'status':'PASS','returncode':got[0],'launches':got[1],'terminal':got[2]}
    result={'status':'PASS','cases':results,'new_inference_calls':0,'actual_launch_calls':0,'actual_service_changes':0}
    (seq.ROOT/'continuity/sequence-cpu-tests.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
