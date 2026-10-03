#!/usr/bin/env bash
set -euo pipefail

CTRL=/home/funboy/StrixHaloClusterDS41/scripts/ds4-speed-001-controller.sh
STATE=/home/funboy/.local/state/strixhalomimo26/perf
mkdir -p "$STATE"

# Stop only MiMo experimental units; never touch unrelated owners.
for u in mimo26-vllm-r0 mimo26-rccl-r0; do
    systemctl --user stop "$u.service" 2>/dev/null || true
    systemctl --user reset-failed "$u.service" 2>/dev/null || true
done
ssh -o IdentityAgent=none -o BatchMode=yes -o ConnectTimeout=5 02-evo-x3-tb '
for u in mimo26-vllm-r1 mimo26-rccl-r1; do
    systemctl --user stop "$u.service" 2>/dev/null || true
    systemctl --user reset-failed "$u.service" 2>/dev/null || true
done
' || true

state="$("$CTRL" status | jq -r .state)"
if [[ "$state" != "READY" ]]; then
    "$CTRL" off >/dev/null || true
    "$CTRL" on >"$STATE/e1-restore-on.json"
fi

deadline=$((SECONDS+1400))
while (( SECONDS < deadline )); do
    s="$("$CTRL" status)"
    st="$(jq -r .state <<<"$s")"
    if [[ "$st" == "READY" ]]; then
        printf '%s
' "$s" >"$STATE/e1-restored.json"
        break
    fi
    sleep 3
done
test "$(jq -r .state "$STATE/e1-restored.json")" = READY

# Product-layer health.
for url in http://127.0.0.1:18223/health http://127.0.0.1:18224/health; do
    code="$(curl -sS -o /dev/null --max-time 3 -w '%{http_code}' "$url" || true)"
    test "$code" = 200
done

# Authenticated natural-stop smoke through the qualified gateway.
python3 - <<'PY'
import http.client, json
from pathlib import Path
token=Path('/home/funboy/.local/state/ds4-document-profile-002/api-token').read_text().strip()
body={
 "model":"deepseek-v4.1-flash",
 "profile":"document-low",
 "messages":[{"role":"user","content":"Return exactly MIMO26-E1-RESTORE-OK."}],
 "temperature":0,"seed":1,"max_tokens":128,"stream":False,
}
c=http.client.HTTPConnection('127.0.0.1',18224,timeout=1800)
c.request('POST','/v1/chat/completions',json.dumps(body).encode(),{
 'Content-Type':'application/json','Authorization':'Bearer '+token})
r=c.getresponse(); raw=r.read(); c.close()
x=json.loads(raw)
choice=(x.get('choices') or [{}])[0]
content=((choice.get('message') or {}).get('content') or '').strip()
out={'http':r.status,'content':content,'finish_reason':choice.get('finish_reason'),
     'pass':r.status==200 and content=='MIMO26-E1-RESTORE-OK' and choice.get('finish_reason')=='stop'}
Path('/home/funboy/.local/state/strixhalomimo26/perf/e1-restore-smoke.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
if not out['pass']: raise SystemExit(2)
PY
