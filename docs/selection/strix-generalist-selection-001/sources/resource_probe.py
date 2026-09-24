"""Read-only peer resource snapshot for a named campaign-owned native worker."""
import argparse
import json
from pathlib import Path
import subprocess
from common import snapshot

p=argparse.ArgumentParser();p.add_argument('--unit',required=True);a=p.parse_args()
if not a.unit.startswith('mimo26-gs001-') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_.@' for c in a.unit):raise SystemExit('not a campaign unit')
cp=subprocess.run(['systemctl','--user','show',a.unit,'-p','MainPID','-p','ActiveState','-p','InvocationID'],capture_output=True,text=True,timeout=5)
fields=dict(line.split('=',1) for line in cp.stdout.splitlines() if '=' in line)
pid=int(fields.get('MainPID','0'))
result={'unit':a.unit,'unit_state':fields,'snapshot':snapshot(pid) if pid>0 else None,'status':'PASS' if pid>0 and fields.get('ActiveState')=='active' else 'UNAVAILABLE'}
print(json.dumps(result))
