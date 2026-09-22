#!/usr/bin/env python3
from __future__ import annotations
import ast
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

RUN = Path(os.environ["MIMO26_RUN_DIR"])
SERVER = os.environ.get("MIMO26_LLAMA_SERVER", "/home/funboy/.local/build/llama.cpp-mimo26-gfx1151/bin/llama-server")
MODEL = os.environ.get("MIMO26_GGUF_MODEL", "/home/funboy/models/MiMo-V2.6/mixed-gguf/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF/MQ-IQ2-XXS-XS-Q8-MM-BF16/MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-00001-of-00004.gguf")
PORT = int(os.environ.get("MIMO26_LLAMA_PORT", "18091"))
CTX = int(os.environ.get("MIMO26_CTX", "4096"))
LOAD_TIMEOUT = float(os.environ.get("MIMO26_LOAD_TIMEOUT", "900"))
MIN_AVAIL = int(os.environ.get("MIMO26_MIN_AVAILABLE_BYTES", str(95 * 1024**3)))

def atomic(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    q = path.with_suffix(path.suffix + ".tmp")
    q.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    os.replace(q, path)

def meminfo():
    out = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        p = v.strip().split()
        if p and p[0].isdigit():
            n = int(p[0])
            out[k] = n * 1024 if len(p) > 1 and p[1] == "kB" else n
    return out

def pstats(pid):
    st = {}
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            st[k] = v.strip()
    stat = Path(f"/proc/{pid}/stat").read_text().split()
    return {
        "pid": pid,
        "VmRSS": st.get("VmRSS"),
        "VmHWM": st.get("VmHWM"),
        "VmSize": st.get("VmSize"),
        "VmSwap": st.get("VmSwap"),
        "minflt": int(stat[9]),
        "majflt": int(stat[11]),
    }

def request(method, path, payload=None, timeout=180):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return resp.status, json.loads(raw.decode()) if raw else {}

def wait_memory():
    start = time.monotonic()
    samples = []
    while True:
        m = meminfo()
        samples.append({
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "MemAvailable": m.get("MemAvailable", 0),
            "SwapFree": m.get("SwapFree", 0),
        })
        atomic(RUN / "memory-wait.json", {"samples": samples[-90:]})
        if m.get("MemAvailable", 0) >= MIN_AVAIL:
            return m
        if time.monotonic() - start > 240:
            raise RuntimeError(f"memory did not recover: available={m.get('MemAvailable', 0)} required={MIN_AVAIL}")
        time.sleep(2)

def code_gate(text):
    code = text.strip()
    tick = chr(96)
    if code.startswith(tick * 3):
        lines = code.splitlines()
        if lines and lines[0].startswith(tick * 3):
            lines = lines[1:]
        if lines and lines[-1].startswith(tick * 3):
            lines = lines[:-1]
        code = "\n".join(lines).strip()
    try:
        tree = ast.parse(code)
    except Exception as e:
        return False, f"parse:{type(e).__name__}:{e}"
    forbidden = (ast.Import, ast.ImportFrom, ast.Attribute, ast.With, ast.AsyncWith, ast.ClassDef, ast.Lambda, ast.Global, ast.Nonlocal, ast.Delete, ast.Try, ast.Raise, ast.While)
    if any(isinstance(n, forbidden) for n in ast.walk(tree)):
        return False, "forbidden_ast"
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(funcs) != 1 or funcs[0].name != "clamp":
        return False, "missing_clamp"
    if any(isinstance(n, ast.Call) for n in ast.walk(tree)):
        return False, "calls_not_allowed"
    ns = {"__builtins__": {}}
    try:
        exec(compile(tree, "<mixed-sanity>", "exec"), ns, ns)
        fn = ns["clamp"]
        for args, expected in [((5,0,10),5),((-1,0,10),0),((99,0,10),10),((3,3,3),3)]:
            got = fn(*args)
            if got != expected:
                return False, f"unit_fail:{args}:{got}!={expected}"
    except Exception as e:
        return False, f"exec:{type(e).__name__}:{e}"
    return True, "PASS"

def complete(prompt, max_tokens):
    t0 = time.perf_counter()
    _, body = request("POST", "/v1/chat/completions", {
        "model": "mimo26-mixed",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    })
    wall = time.perf_counter() - t0
    choice = body["choices"][0]
    msg = choice.get("message", {})
    return {
        "text": (msg.get("content") or "").strip(),
        "reasoning_content": msg.get("reasoning_content"),
        "finish_reason": choice.get("finish_reason"),
        "usage": body.get("usage"),
        "wall_s": wall,
        "raw_message": msg,
    }

def sanity():
    specs = [
        ("arithmetic", "Compute 17*19. Return only the integer.", lambda s: s == "323"),
        ("extract", "Read this exact token: ZEBRA-4821. Return only that token.", lambda s: s == "ZEBRA-4821"),
        ("json", 'Return only valid JSON with exactly these values: alpha is integer 7 and beta is string "blue".', lambda s: json.loads(s) == {"alpha": 7, "beta": "blue"}),
        ("italian", "Nel testo seguente il colore dichiarato è cobalto. Rispondi solo con il nome del colore.", lambda s: s.casefold() == "cobalto"),
        ("english", "Alice is first and Bob is second. Who is second? Return only the name.", lambda s: s == "Bob"),
    ]
    tests = []
    for name, prompt, check in specs:
        r = complete(prompt, 64)
        try:
            ok = bool(check(r["text"]))
            reason = "PASS" if ok else "expected_mismatch"
        except Exception as e:
            ok = False
            reason = f"check:{type(e).__name__}:{e}"
        tests.append({"name": name, "prompt": prompt, "pass": ok, "reason": reason, **r})
        atomic(RUN / "quality.json", {"status": "IN_PROGRESS", "tests": tests, "thinking": False, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    prompt = "Return only Python code defining clamp(x, lo, hi). It must return lo when x < lo, hi when x > hi, otherwise x. Do not import anything and do not call other functions."
    r = complete(prompt, 96)
    ok, reason = code_gate(r["text"])
    tests.append({"name": "code_clamp", "prompt": prompt, "pass": ok, "reason": reason, **r})
    out = {"status": "PASS" if all(x["pass"] for x in tests) else "FAIL", "tests": tests, "thinking": False, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    atomic(RUN / "quality.json", out)
    return out

def self_test():
    good = "def clamp(x, lo, hi):\n    if x < lo: return lo\n    if x > hi: return hi\n    return x"
    assert code_gate(good)[0]
    assert not code_gate("323")[0]
    print("MIXED_SINGLE_WORKER_SELFTEST_PASS")

def main():
    if "--self-test" in sys.argv:
        self_test()
        return 0
    RUN.mkdir(parents=True, exist_ok=True)
    before = meminfo()
    ready_mem = wait_memory()
    atomic(RUN / "memory-before-load.json", {"before_wait": before, "after_wait": ready_mem})
    cmd = [
        SERVER, "-m", MODEL, "-c", str(CTX), "-np", "1",
        "--host", "127.0.0.1", "--port", str(PORT),
        "--gpu-layers", "999", "--load-mode", "none", "--lazy-mode", "off",
        "--reasoning", "off", "--jinja",
        "--chat-template-kwargs", '{"enable_thinking":false}',
    ]
    atomic(RUN / "server-command.json", {"argv": cmd})
    log = (RUN / "llama-server.log").open("ab", buffering=0)
    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, preexec_fn=os.setsid)
    atomic(RUN / "server-process.json", {"pid": proc.pid, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    def stop(sig=None, frame=None):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
        if sig is not None:
            raise SystemExit(128 + sig)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        last = None
        while time.perf_counter() - t0 < LOAD_TIMEOUT:
            if proc.poll() is not None:
                raise RuntimeError(f"llama-server exited during load rc={proc.returncode}")
            try:
                status, body = request("GET", "/health", timeout=3)
                last = {"status": status, "body": body}
                if status == 200:
                    break
            except Exception as e:
                last = {"error": f"{type(e).__name__}:{e}"}
            atomic(RUN / "health-last.json", last)
            time.sleep(2)
        else:
            raise TimeoutError(f"server not healthy within {LOAD_TIMEOUT}s; last={last}")
        load_s = time.perf_counter() - t0
        mi = meminfo()
        ps = pstats(proc.pid)
        atomic(RUN / "load.json", {
            "status": "PASS", "load_s": load_s, "pid": proc.pid,
            "model": MODEL, "ctx": CTX, "parallel": 1,
            "load_mode": "none", "lazy_mode": "off", "gpu_layers": 999,
            "process": ps, "meminfo": mi,
            "swap_used": mi.get("SwapTotal",0) - mi.get("SwapFree",0),
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        })
        pf0 = pstats(proc.pid)
        q = sanity()
        pf1 = pstats(proc.pid)
        mi2 = meminfo()
        atomic(RUN / "memory-after-quality.json", {
            "process_before_quality": pf0, "process_after_quality": pf1,
            "minor_fault_delta": pf1["minflt"] - pf0["minflt"],
            "major_fault_delta": pf1["majflt"] - pf0["majflt"],
            "meminfo": mi2,
            "swap_used": mi2.get("SwapTotal",0) - mi2.get("SwapFree",0),
        })
        return 0 if q["status"] == "PASS" else 40
    except Exception as e:
        atomic(RUN / "worker-error.json", {"type": type(e).__name__, "message": str(e), "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "server_rc": proc.poll()})
        raise
    finally:
        stop()

if __name__ == "__main__":
    raise SystemExit(main())
