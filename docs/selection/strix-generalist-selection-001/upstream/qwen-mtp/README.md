---
license: other
license_name: qwen-community-1.0
license_link: https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/LICENSE
base_model:
- Qwen/Qwen3.8-Flash-Next
tags:
- gguf
- llama.cpp
- speculative-decoding
- mtp
- qwen4exp
- strix-halo
- vulkan
---

# Qwen3.8-Flash-Next draft head — 32–61 tok/s on Strix Halo

*A [Vitronia](https://github.com/drluoto/flash-next-strix-halo) project.*

> **20 Sep 2026 — new default is Q5_K, not Q8_0.** A lighter draft head turned out to
> be faster *and* to get accepted more often: +2.8 % mean across six workloads, +8.7 %
> on prose. Grab `mtp-Qwen3.8-Flash-Next-Q5_K-frspec-65k.gguf` under Files. Q8_0 stays
> up and still works. Numbers under [What it buys](#what-it-buys), and the reason the
> file is requantised rather than built clean is under
> [Provenance](#provenance) — it measured better that way, which surprised me too.
>
> **Still Vulkan, not ROCm** (17 Sep): ROCm returns wrong answers on this chip without
> telling you. The old ROCm table is at the bottom.

A small head that guesses the next few tokens so the big model can verify several at
once. Useless on its own — it only runs alongside the full model.

Part of an ongoing project to optimise Qwen3.8-Flash on Strix Halo. Some of the dev
work is my own, some builds on community releases. When I have time I try to merge
upstream. [Full stack and numbers](https://github.com/drluoto/flash-next-strix-halo).

## Which file

| File | Size | |
|---|---|---|
| [`mtp-Qwen3.8-Flash-Next-Q5_K-frspec-65k.gguf`](https://huggingface.co/drluoto/Qwen3.8-Flash-Next-MTP-GGUF/blob/main/mtp-Qwen3.8-Flash-Next-Q5_K-frspec-65k.gguf) | 2.70 GB | **Start here.** Smaller and faster than the Q8_0 below. |
| [`mtp-Qwen3.8-Flash-Next-Q8_0-frspec-65k.gguf`](https://huggingface.co/drluoto/Qwen3.8-Flash-Next-MTP-GGUF/blob/main/mtp-Qwen3.8-Flash-Next-Q8_0-frspec-65k.gguf) | 3.64 GB | Previous default. Still fine. |
| [`mtp-Qwen3.8-Flash-Next-Q8_0.gguf`](https://huggingface.co/drluoto/Qwen3.8-Flash-Next-MTP-GGUF/blob/main/mtp-Qwen3.8-Flash-Next-Q8_0.gguf) | 4.14 GB | Full vocabulary. Use if the trimmed ones guess badly on your workload. |
| [`mtp-Qwen3.8-Flash-Next-Q4_K_M.gguf`](https://huggingface.co/drluoto/Qwen3.8-Flash-Next-MTP-GGUF/blob/main/mtp-Qwen3.8-Flash-Next-Q4_K_M.gguf) | 2.79 GB | Tight on memory. |
| [`mtp-Qwen3.8-Flash-Next-Q5_K-frspec-65k-bf16path.gguf`](https://huggingface.co/drluoto/Qwen3.8-Flash-Next-MTP-GGUF/blob/main/mtp-Qwen3.8-Flash-Next-Q5_K-frspec-65k-bf16path.gguf) | 2.70 GB | Same size as the Q5_K above, built straight from bf16. Slower here, see Provenance. |
| [`mtp-Qwen3.8-Flash-Next-bf16.gguf`](https://huggingface.co/drluoto/Qwen3.8-Flash-Next-MTP-GGUF/blob/main/mtp-Qwen3.8-Flash-Next-bf16.gguf) | 7.78 GB | Reference. |

## Running it

The model this is measured against is
[AgenticRequant Q5K](https://huggingface.co/drluoto/Qwen3.8-Flash-Next-AgenticRequant-Q5K-GGUF)
— Qwen3.8-Flash-Next requantised by measured read frequency.

```sh
llama-server -m trunk-q5k-00001-of-00003.gguf \
  -md mtp-Qwen3.8-Flash-Next-Q5_K-frspec-65k.gguf \
  --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-p-min 0.0 \
  -fa 1 -ub 2048 -b 2048 -c 262144 -np 2 -lm dio --jinja
```

Loading a detached draft head needs a build that supports it. Still
[under review upstream](https://github.com/ggml-org/llama.cpp/pull/27836); ours has it:
[`drluoto/llama.cpp`, branch `strix-halo-vulkan`](https://github.com/drluoto/llama.cpp/tree/strix-halo-vulkan).

On AMD, pin the GPU clock first (`rocm-smi -d 0 --setperflevel high`). On `auto` it
floats and you lose about 20 %.

## What it buys

The Q5_K head is what I recommend for running our full stack. It gives both higher
speed **and** higher acceptance than the Q8_0, which is not what you'd expect from a
smaller head. The draft LM head is 81 % of the bytes read per drafted token, so making
it cheaper pays directly, and it turns out that doesn't cost you guess quality here.

This is only tested on our full stack. The numbers below are **whole-stack decode
throughput** — the big model and the draft head together, as you'd actually run them —
not the draft head measured on its own. On a different target, a different trunk quant
or a different backend, you may land somewhere else.

Ryzen AI Max+ 395, 128 GB, Vulkan, our 86 GB Q5_K trunk, `--spec-draft-n-max 3
--spec-draft-p-min 0.0`. Two interleaved rounds, GPU clock pinned, greedy.

**Full-stack decode, tok/s:**

| Workload | Q8_0 65k head | Q5_K 65k head | |
|---|---:|---:|---|
| short code | 58.2 | **60.9** | +4.6 % |
| new code @8k | 43.0 | 43.2 | +0.6 % |
| prose @8k | 29.4 | **31.9** | +8.7 % |
| rewrite @8k | 55.2 | 56.2 | +1.6 % |
| new code @32k | 37.1 | 37.8 | +1.6 % |
| rewrite @32k | 48.4 | 49.1 | +1.4 % |
| mean | 45.2 | **46.5** | +2.8 % |

Acceptance went up rather than down: 0.86 → 0.89 on short code, 0.35 → 0.39 on prose.
The gain tracks acceptance — biggest where it's lowest, nothing on the two workloads
where it's already 1.00. That's where you pay for drafts you don't get to keep.

[KYmidnight](https://github.com/ggml-org/llama.cpp/discussions/27950) pointed out that
a draft matched to the target beats a higher-bpw one; these are our numbers on our box
after following that up.

Greedy output is deterministic run to run, but it is *not* identical to what the Q8_0
head produces. Changing the draft changes which tokens get verified together, and
floating-point reduction order goes with it. Different, not worse: same answers on
arithmetic at 24k context, tool calls, long-output corruption checks and vision.

## Provenance

Converted from the official checkpoint. Only the draft-head tensors were fetched —
7.3 GB out of 360 GB, via range reads on the safetensors shards. 31 draft tensors plus
shared embeddings and lm_head.

**The Q5_K file is deliberately requantised from Q8_0, not built straight from bf16.**
That sounds wrong, so here is the measurement. We built both and ran the same bench:

| Workload | requantised via Q8_0 | straight from bf16 |
|---|---:|---:|
| short code | 61.0 (acc 0.89) | 58.5 (acc 0.84) |
| new code @8k | 43.3 (acc 0.65) | 42.4 (acc 0.64) |
| prose @8k | 31.9 (acc 0.39) | 29.9 (acc 0.35) |
| rewrite @8k | 56.2 (acc 1.00) | 56.1 (acc 1.00) |
| rewrite @32k | 49.1 (acc 1.00) | 49.0 (acc 1.00) |

Where acceptance is already 1.00 the two are the same. Where it isn't, the requantised
one wins. Our guess: the target is itself a requant (UD-IQ4_XS → Q5_K), and a draft that
went the same route agrees with it better. What matters for acceptance is that draft and
target agree, not that the draft is faithful to the original weights. We have not proved
that — it would need the same two drafts against a target that isn't a requant.

If you run a different target, the cleaner build may well be the better one. It is here
as `…-Q5_K-frspec-65k-bf16path.gguf` so you can measure it yourself.

```
Q5_K frspec-65k          282764bf3ce11b1f…
Q5_K frspec-65k bf16path 5d6d6b19c61cb9f1…
Q8_0 frspec-65k          c9c505c1f68f0088…
Q8_0                     b9880220df29fc22…
Q4_K_M                   8db8b4207bbe4028…
bf16                     395e8c8c2215bfaf…
```

Trimming script and frequency map:
[branch `frspec-qwen4exp-strix`](https://github.com/drluoto/llama.cpp/tree/frspec-qwen4exp-strix),
under `scripts/frspec`.

Long outputs checked for corruption. Earlier community ports of this head degraded into
garbage past roughly 1k tokens of prompt. This one doesn't.

## Old ROCm numbers (Aug 2026)

ROCm 7.1, stock UD-IQ4_XS target, before the move to Vulkan.

| Workload | no draft head | with |
|---|---:|---:|
| file rewrite @8k | 17 tok/s | 47 |
| new code @8k | 17 | 32 |
| file rewrite @24k | 15 | 29 |
| new code @24k | 15 | 25 |

---

Built with Claude Fable 5.1. A Vitronia project.
