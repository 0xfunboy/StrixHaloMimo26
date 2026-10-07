#!/usr/bin/env python3
"""Minimal OpenAI-compatible client for the private MiMo service forwarded to NODE01."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?")
    parser.add_argument("--base", default="http://127.0.0.1:18571/v1")
    parser.add_argument("--model", default="mimo-mopd-kyojin")
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--system")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    prompt = args.prompt if args.prompt is not None else sys.stdin.read()
    if not prompt.strip():
        raise SystemExit("prompt required")
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": args.model,
        "messages": messages,
        "max_completion_tokens": args.max_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "stream": args.stream,
    }
    request = urllib.request.Request(
        args.base.rstrip("/") + "/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=3600) as response:
            if not args.stream:
                result = json.load(response)
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    message = result["choices"][0]["message"]
                    if message.get("reasoning_content"):
                        print(message["reasoning_content"], file=sys.stderr)
                    print(message.get("content", ""))
                return
            for raw in response:
                line = raw.decode(errors="replace").rstrip("\r\n")
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                event = json.loads(payload)
                for choice in event.get("choices", []):
                    delta = choice.get("delta", {})
                    if delta.get("reasoning_content"):
                        print(delta["reasoning_content"], end="", file=sys.stderr, flush=True)
                    if delta.get("content"):
                        print(delta["content"], end="", flush=True)
            print()
    except urllib.error.HTTPError as exc:
        sys.stderr.write(exc.read().decode(errors="replace") + "\n")
        raise


if __name__ == "__main__":
    main()
