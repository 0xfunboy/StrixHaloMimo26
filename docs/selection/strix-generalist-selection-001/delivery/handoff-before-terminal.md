# STRIX-GENERALIST-SELECTION-001: verified checkpoint

Observed: 2026-09-24T16:13:04.867741+02:00
Base: 87442a8e1b999e5f33165d0b6b563eac5248ab15. Continuity: efae11dae82e322f581db0de1d3ad0226e5ce37d.
Source indexes and all 74+15 preregistered files remain unchanged. See preparation.json, continuity/preparation.json, QWEN_HISTORY_AND_REUSE.md.

## Q / generalist-selection-001-Q-001
{"exists": true, "completion": "PASS", "load": {"status": "PASS", "load_s": 95.56661623797845, "pid": 754146, "error": null}, "primary_records": 32, "cleanup": {"status": "PASS", "k2_state": "READY", "at": "2026-09-24T10:53:53+0200", "epoch": "1790239745036780819", "target": {"controller": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6/runtime/ds41/serve-controller.sh", "release": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6", "preset": "dspark-k2-gfx1151", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513"}}, "fatal.json": null, "mtp-off-blocker.json": {"status": "BLOCKED", "phase": "mtp_off_after_primary_complete", "error": "RuntimeError:MTP_PROCESS_MODE_UNPROVEN:None", "primary_records_preserved": 32, "at": "2026-09-24T10:49:02+0200"}}
Unit: {"LoadState": "not-found", "ActiveState": "inactive", "SubState": "dead", "InvocationID": "", "MainPID": "0", "Result": "success", "ExecMainStatus": "0"}
Raw: /home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-Q-001

## M / generalist-selection-001-M-001
{"exists": true, "completion": "FAILED", "load": {"status": "PASS", "load_s": 114.18077592900954, "pid": 766173, "error": null}, "primary_records": 6, "cleanup": {"status": "PASS", "k2_state": "READY", "at": "2026-09-24T11:01:01+0200", "epoch": "1790240178624599071", "target": {"controller": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6/runtime/ds41/serve-controller.sh", "release": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6", "preset": "dspark-k2-gfx1151", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513"}}, "fatal.json": {"phase": "preflight", "status": "TECHNICAL_ERROR", "error": "RuntimeError:SANITY_PREFLIGHT_FAIL", "at": "2026-09-24T10:56:15+0200"}, "mtp-off-blocker.json": null}
Unit: {"LoadState": "loaded", "ActiveState": "failed", "SubState": "failed", "InvocationID": "6873be3ac79e4339bf7a94b361ebc40b", "MainPID": "0", "Result": "exit-code", "ExecMainStatus": "32"}
Raw: /home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-M-001

## D / generalist-selection-001-D-002
{"exists": true, "completion": "PASS", "load": {"status": "PASS", "load_s": 132.3360888559837, "pid": 777630, "error": null}, "primary_records": 32, "cleanup": {"status": "PASS", "k2_state": "READY", "at": "2026-09-24T12:43:29+0200", "epoch": "1790246320305924015", "target": {"controller": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6/runtime/ds41/serve-controller.sh", "release": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6", "preset": "dspark-k2-gfx1151", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513"}}, "fatal.json": null, "mtp-off-blocker.json": null}
Unit: {"LoadState": "not-found", "ActiveState": "inactive", "SubState": "dead", "InvocationID": "", "MainPID": "0", "Result": "success", "ExecMainStatus": "0"}
Raw: /home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-002

## O / generalist-selection-001-O-001
{"exists": true, "completion": "RUNNING", "load": {"status": "IN_PROGRESS", "load_s": null, "pid": null, "error": null}, "primary_records": null, "cleanup": {"status": "PENDING"}, "fatal.json": null, "mtp-off-blocker.json": null}
Unit: {"LoadState": "loaded", "ActiveState": "active", "SubState": "running", "InvocationID": "d6b3ceab8b014239888b9f47041646ed", "MainPID": "805104", "Result": "success", "ExecMainStatus": "0"}
Raw: /home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-O-001

## T / generalist-selection-001-QMTP-001
{"exists": false, "completion": null, "load": null, "primary_records": null, "cleanup": null, "fatal.json": null, "mtp-off-blocker.json": null}
Unit: {"LoadState": "not-found", "ActiveState": "inactive", "SubState": "dead", "InvocationID": "", "MainPID": "0", "Result": "success", "ExecMainStatus": "0"}
Raw: /home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-QMTP-001

## D_SETUP / generalist-selection-001-D-001
{"exists": true, "completion": "INTERRUPTED", "load": {"status": "IN_PROGRESS", "load_s": null, "pid": null, "error": null}, "primary_records": null, "cleanup": {"status": "PASS", "k2_state": "READY", "at": "2026-09-24T11:19:59+0200", "epoch": "1790241311047078402", "target": {"controller": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6/runtime/ds41/serve-controller.sh", "release": "/home/funboy/.local/share/haloclu-ds41/releases/k2-prefill-5bdfed6", "preset": "dspark-k2-gfx1151", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513"}}, "fatal.json": {"phase": "load", "status": "INTERRUPTED", "signal": 15, "at": "2026-09-24T11:15:09+0200"}, "mtp-off-blocker.json": null}
Unit: {"LoadState": "loaded", "ActiveState": "failed", "SubState": "failed", "InvocationID": "fc1b2de966c14058a8e629179516d1bb", "MainPID": "0", "Result": "exit-code", "ExecMainStatus": "143"}
Raw: /home/funboy/.local/state/strixhalomimo26/windows/generalist-selection-001-D-001

## Resident
{"state": "OFF", "preset": "dspark-k2-gfx1151", "release_id": "5bdfed698ab97b6230db3fe8a7e37ff8e9b3d513", "owner": "NONE", "owner_state": "OFF", "epoch": "", "reason": "", "ranks": [{"rank": 0, "active": false, "health_http": "000"}, {"rank": 1, "active": false, "health_http": "000"}], "paired_backend_http": "000"}

NEXT EXACT ACTION: reconcile the earliest existing nonterminal run and its supervised restore. Never replay an uncertain request or redispatch an existing run. Once terminal/restored, continue only the remaining authorized Q/M/D/O/T order through launch_continuity_v1.py; technical failures require an explicit isolated blocker. After all permitted windows, CPU audit/evaluation and local delivery; no new experiment. No push/deployment, tuning, new download or changes to resident releases. K2 EngineCore processes after restore are legitimate residents.
