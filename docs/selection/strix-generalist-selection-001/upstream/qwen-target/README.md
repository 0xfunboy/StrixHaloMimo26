---
license: other
license_name: qwen-community-1.0
license_link: https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/LICENSE
base_model:
- Qwen/Qwen3.8-Flash-Next
tags:
- agentic
- gguf
- llama.cpp
- qwen4exp
- strix-halo
- vulkan
- quantized
---

# Qwen3.8-Flash-Next — AgenticRequant

*AgenticRequant by [Vitronia](https://github.com/drluoto/flash-next-strix-halo).*

Part of a full stack for running this model on a single Strix Halo box: the engine
branch, the draft head, the measurements and the pitfalls are all at
[drluoto/flash-next-strix-halo](https://github.com/drluoto/flash-next-strix-halo).

This is a project to continuously optimise the Qwen3.8-Flash MoE model for my Strix
Halo. Some of the optimisations may be relevant to other hardware. When I have time I
try to merge upstream.

Most quants spread their bits evenly across the file. That wastes them, because a
125B MoE does not read its weights evenly. So I measured what this model actually
touches while doing agentic work — real coding-agent turns replayed from my own
logs, plus code, prose and file-rewrite workloads — and spent the bits where the
reads are.

Two measurements, two decisions:

- **Bytes read per token, per tensor group.** The trunk is read *in full, every
  token*; only 10 of 512 experts are touched. The trunk turned out to be ~80 % of
  the bytes moved despite being a small share of the file. It got the bits (IQ4_XS →
  Q5_K), the experts kept theirs.
- **Token frequency across real agent traces.** Ten real agent turns pulled from my
  assistant's database, weighted 5×, plus code, English and Swedish. That ranking is
  what let the [draft head](https://huggingface.co/drluoto/Qwen3.8-Flash-Next-MTP-GGUF)
  cut its vocabulary to the 65k tokens the work actually uses.

Net: **+13 % decode**, 1.4 GB smaller, 0.91 % perplexity. The quant alone, same
build, same traces, speculation off — see below.

## What changed

| | Original UD-IQ4_XS | This requant |
|---|---|---|
| trunk (351 tensors) | IQ4_XS | **Q5_K** |
| router (48 tensors) | F32 | **Q8_0** |
| experts | IQ4_NL / IQ3_S | unchanged |
| n-gram table | IQ4_NL | unchanged |

The measurement that decided this is in the repo: bytes-per-token per tensor group,
computed from the tensor table, then checked against measured bandwidth (208–226 GB/s
on this chip). The trunk is 4.68 GB/token, the experts 1.16 GB/token.

### The agentic bench

Two kinds of workload, because they fail differently:

- **Replayed real turns.** Ten conversations pulled straight out of my assistant's
  database — full history up to a user turn, tool calls included, sampling fields
  omitted exactly as the real client omits them. Replayed against the server, medians
  reported. These are messy and long, and they're what the machine actually does.
- **Six synthetic loads** at fixed shapes: short code, new code and prose at 8k, file
  rewrite at 8k, new code and rewrite at 32k. Temp 0, prompt cache off. These are
  reproducible and catch regressions the replays would hide in noise.

Draft acceptance splits sharply between them: 1.00 on file rewrite, 0.35 on prose.
That's the single most useful number for predicting speed on your own work.

## What the requant itself bought

**This is the quant alone.** Same build, same replayed traces, **speculation off on both
sides**, so it isolates the quantisation from everything else in the stack.

| | decode tok/s | prefill tok/s | bytes/token |
|---|---:|---:|---:|
| original UD-IQ4_XS | 23.8 | 259 | 5.84 GB |
| **AgenticRequant** | **27.0** | **278** | **4.49 GB** |
| | **+13 %** | **+7 %** | **−23 %** |

Worth noting what that gap says: bytes per token fell 23 % but speed rose only 13 %.
The difference is a fixed per-token cost that isn't bandwidth — roughly 15 ms of a
37 ms step, on the GPU side. Quantisation can't touch it. That's a ceiling anyone
requantising this architecture will hit, and it's why the trunk is the only place
worth spending bits.

## Quality

Wikitext-2, 580 chunks, `n_ctx=512`, same binary and flags, one model at a time,
GPU clock pinned.

| Model | Size | Perplexity |
|---|---:|---:|
| unsloth UD-IQ4_XS | 93.7 GB | 4.7393 ± 0.0291 |
| AgenticRequant | **92.3 GB** | 4.7823 ± 0.0295 |
| difference | −1.4 GB | **+0.91 %** |

Error bars overlap. Perplexity measures English prose, so it says nothing about tool
calls, code, long contexts or other languages. Those are covered by a separate gate
(arithmetic at 24k context, tool calling, a long answer past the corruption
threshold, vision) which this model passes.

## Speed of the whole stack

**These numbers are not the quant on its own.** They are this model *plus* the draft
head, our engine branch and a pinned GPU clock — the setup described under
[Running it](#running-it). The quant's own contribution is the +13 % above; the rest
comes from speculative decoding, which is why the spread is so wide.

Ryzen AI Max+ 395 (Radeon 8060S, 128 GB shared memory), Vulkan, one request at a
time, temp 0, no prompt cache, `--spec-type draft-mtp --spec-draft-n-max 3`.
Decode tokens/second:

| Workload | tok/s |
|---|---:|
| short code, empty context | 58 |
| new code @8k | 43 |
| prose @8k | 29 |
| file rewrite @8k | 55 |
| new code @32k | 37 |
| file rewrite @32k | 48 |

Prompt reading: 518 tok/s at 8k, 402 at 32k.

The spread is draft acceptance, not the quant: 1.00 on file rewrite (the output is
mostly already in the input, so the draft head guesses right every time) against 0.35
on prose. Drop the draft head and everything lands near 27.
[What makes the difference, and what didn't work](https://github.com/drluoto/flash-next-strix-halo).

## Files

| File | Size | sha256 |
|---|---:|---|
| `trunk-q5k-00001-of-00003.gguf` | 0.01 GB | `89cfaf22a1284938…` |
| `trunk-q5k-00002-of-00003.gguf` | 49.4 GB | `558e3549bd7c03b6…` |
| `trunk-q5k-00003-of-00003.gguf` | 42.9 GB | `204f1e580f2ea9c0…` |

Point `-m` at shard 1; llama.cpp finds the rest.

## Running it

```sh
llama-server -m trunk-q5k-00001-of-00003.gguf \
  -md mtp-Qwen3.8-Flash-Next-Q8_0-frspec-65k.gguf \
  --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-p-min 0.0 \
  -fa 1 -ub 2048 -b 2048 -c 262144 -np 2 -lm dio --jinja
```

The draft head is [here](https://huggingface.co/drluoto/Qwen3.8-Flash-Next-MTP-GGUF).
You need a build that can load a detached draft head — support is still
[under review upstream](https://github.com/ggml-org/llama.cpp/pull/27836). Ours has it:
[`drluoto/llama.cpp`, branch `strix-halo-vulkan`](https://github.com/drluoto/llama.cpp/tree/strix-halo-vulkan).

On AMD, pin the GPU clock first (`rocm-smi -d 0 --setperflevel high`). With `auto` the
clock floats 2340–2540 MHz against a 2900 max and you lose about 20 %.

## How it was made

```sh
LLAMA_QUANT_ALLOW_ROUTER=1 llama-quantize --allow-requantize \
  --tensor-type-file tensortyper-q5k.txt --keep-split \
  Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf trunk-q5k.gguf Q5_K 12
```

`tensortyper-q5k.txt` (1152 lines, one tensor per line) is in this repo. The router
needs `LLAMA_QUANT_ALLOW_ROUTER=1`: llama.cpp hard-locks `ffn_gate_inp` to F32
(`src/llama-quant.cpp:318`), which costs 0.25 GB read on every token. Our branch adds
the env gate; stock llama.cpp will refuse.

Resulting tensor types:

| Type | Tensors | GB |
|---|---:|---:|
| IQ4_NL | 44 | 49.1 |
| IQ3_S | 94 | 33.9 |
| Q8_0 | 199 | 5.6 |
| Q5_K | 339 | 2.1 |
| IQ4_XS | 2 | 0.9 |
| Q6_K | 13 | 0.7 |

The GGUF reports `file_type = MOSTLY_Q5_K_M`, which is the base type passed to
`llama-quantize` — hence the Q5K in the name. Note that by bytes the file is mostly
IQ4_NL and IQ3_S: those are the experts, left exactly as unsloth had them. Q5_K is
only 2.1 GB, but it's the 2.1 GB that gets read on every single token.

## What this is not

Not a general-purpose quant. It's tuned for a machine where memory bandwidth is the
limit and the whole model is resident. On a GPU that offloads experts to system RAM,
the tradeoff runs the other way and the original is the better choice.

---

AgenticRequant by Vitronia. Built with Claude.
