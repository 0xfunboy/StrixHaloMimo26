---
license: mit
base_model: XiaomiMiMo/MiMo-V2.6-Flash-RL
base_model_relation: quantized
pipeline_tag: image-text-to-text
library_name: gguf
language:
  - en
  - zh
tags:
  - gguf
  - mixed-quant
  - mimo_v2
  - multimodal
  - audio
  - video-understanding
  - imatrix
  - dgx-spark
---

# MiMo-V2.6-Flash-RL Mixed-Quant GGUF

> **Mixed weights with original-representation calibration.** The four-shard language model passed its 508-tensor structural and quantization audit.
>
> **Role-aware precision:** expert gate/up **IQ2_XXS**, expert down **IQ2_XS**, shared dense paths and embedded MTP **Q8_0**, media **BF16**, and numerical controls **F32**.
>
> **Measured GGUF storage: 93.092 GB / 86.699 GiB**, including main model, multimodal projector and separate DFlash weights. Auxiliary files and runtime memory are additional.
>
> Text, image, audio, video and audiovisual assets are retained. **ds4-dfm-rs integration and DGX Spark qualification remain unfinished.** Artifact availability does not establish end-to-end serving support.

## Support my work

I work on making large language models practical on constrained hardware through mixed quantization, inference optimization, and serving experiments. Contributions help cover calibration, GPU compute, storage, and testing so these results can be published openly.

<a href="https://www.buymeacoffee.com/baekpica" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" style="height: 60px !important;width: 217px !important;"></a> <a href="https://github.com/sponsors/Baekpica" target="_blank"><img src="https://img.shields.io/badge/Sponsor-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white" alt="Sponsor Baekpica on GitHub" style="height: 60px !important;width: 217px !important;"></a>

This is a mixed-precision conversion of [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL), pinned to revision [`3b38d063180c3e4aed9691fdc735f3d10b266ee4`](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/tree/3b38d063180c3e4aed9691fdc735f3d10b266ee4).

## Why this model needs an asymmetric layout

The source stores routed expert weights as packed MXFP4. Two logical weights occupy each packed byte, so counting stored tensor elements can produce a roughly 159B figure. The expanded language trunk contains approximately **308.78B logical parameters**; the root checkpoint including embedded MTP and media components contains approximately **310.76B**, excluding the separate DFlash package. The packed representation does not make this a 159B logical model.

Routed experts account for **302.80B parameters**. They dominate the storage budget, so the recipe concentrates compression there and gives their output projections a higher tier. Shared attention and dense paths, the output head, and multimodal components receive substantially more precision.

## Variant and availability

| Component | Precision | Measured GB | Measured GiB |
|---|---|---:|---:|
| Main model including three embedded MTP blocks | IQ2_XXS / IQ2_XS / Q8_0 / F32 | 88.778 | 82.681 |
| Multimodal projector | BF16 / F32 | 2.749 | 2.560 |
| Separate DFlash | Q8_0 / F32 | 1.566 | 1.458 |
| **All GGUF weights** | Mixed | 93.092 | 86.699 |

Main plus media without the optional separate drafter: **91.526 GB / 85.240 GiB**.

| File | Bytes |
|---|---:|
| [MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-00001-of-00004.gguf](MQ-IQ2-XXS-XS-Q8-MM-BF16/MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-00001-of-00004.gguf) | 22,470,644,192 |
| [MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-00002-of-00004.gguf](MQ-IQ2-XXS-XS-Q8-MM-BF16/MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-00002-of-00004.gguf) | 22,464,695,232 |
| [MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-00003-of-00004.gguf](MQ-IQ2-XXS-XS-Q8-MM-BF16/MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-00003-of-00004.gguf) | 22,464,695,232 |
| [MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-00004-of-00004.gguf](MQ-IQ2-XXS-XS-Q8-MM-BF16/MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8-00004-of-00004.gguf) | 21,377,729,024 |
| [mmproj-MiMo-V2.6-Flash-RL-BF16.gguf](MQ-IQ2-XXS-XS-Q8-MM-BF16/mmproj-MiMo-V2.6-Flash-RL-BF16.gguf) | 2,748,509,792 |
| [MiMo-V2.6-Flash-RL-DFlash-Q8_0.gguf](MQ-IQ2-XXS-XS-Q8-MM-BF16/MiMo-V2.6-Flash-RL-DFlash-Q8_0.gguf) | 1,565,911,104 |

Download the complete variant, including template, DFlash configuration and provenance:

```bash
hf download Baekpica/MiMo-V2.6-Flash-RL-Mixed-Quant-GGUF \
  --include 'MQ-IQ2-XXS-XS-Q8-MM-BF16/*' --local-dir ./mimo-mixed
cd ./mimo-mixed/MQ-IQ2-XXS-XS-Q8-MM-BF16
sha256sum -c SHA256SUMS
```

These are download/verification commands. Serving commands await runtime qualification.

## Quantization targets

| Model region | Target | Reason |
|---|---|---|
| Routed expert `gate` and `up` | **IQ2_XXS** | Largest share of the parameter budget |
| Routed expert `down` | **IQ2_XS** | Higher precision at the return to the residual stream |
| Attention projections and dense FFN matrices | **Q8_0** | Shared computation on every token |
| Token embedding and output head | **Q8_0** | Preserve input and logit precision |
| Three embedded MTP blocks, eligible matrices | **Q8_0** | Preserve checkpoint predictors for later runtime integration |
| Routers, norms, attention sinks, and control tensors | **F32** | Preserve routing and numerical control |
| Multimodal encoder/projector matrices | **BF16** | Preserve media representation precision |
| Separate DFlash draft matrices | **Q8_0** | Optional draft package, separate from embedded MTP |

The [per-tensor inventory](MQ-IQ2-XXS-XS-Q8-MM-BF16/expected-mixed-inventory.json) and [recipe](MQ-IQ2-XXS-XS-Q8-MM-BF16/quant-recipe.json) accompany the weights. BF16/F32 in this table describes the output storage format; source tensors already stored in FP8 are expanded from that source precision.

## Importance matrix and calibration

Calibration uses the original checkpoint representation: expert MXFP4 values are repacked into GGUF without an additional quantization step, while the source FP8 dense tensors are expanded to BF16. This reference is **not an original full-BF16 checkpoint** and is not calibrated from the final IQ2 artifact.

The corpus starts from [Baekpica/Inkling-Small-Multimodal-Calibration](https://huggingface.co/datasets/Baekpica/Inkling-Small-Multimodal-Calibration), with media recovered from the source datasets and prompts tokenized using MiMo's own tokenizer. Inkling token IDs and embeddings are not reused. Video clips are added from [FineVideo](https://huggingface.co/datasets/HuggingFaceFV/finevideo).

| Prepared subset | Records | Current state |
|---|---:|---|
| Text reasoning and code/tool text | 667 | Completed 640 × 1,024-token chunks (655,360 tokens) |
| Chart/document images | 486 | Native trunk calibration completed |
| Audio | 309 | Native trunk calibration completed |
| FineVideo clips | 79 | Native trunk calibration completed |
| FineVideo joint audiovisual clips | 79 | Native audiovisual trunk calibration completed |
| FineVideo holdout | 9 | Separated by source video; not part of calibration |

The visual-only clips are paired with a separate set of 79 joint audiovisual inputs using restored original audio and production per-frame-pair interleaving. Every prepared audio token is consumed exactly once in each joint input. All 953 native media records completed trunk calibration with finite final logits. Coverage is 12,030 of 12,032 layer/expert pairs; block 7 experts 13 and 184 remain unobserved. The original recipe is unchanged: raw zero counts are retained and the pinned quantizer uses uniform importance weights for those experts. The final imatrix SHA256 is `265cc19bc1470b95a9157d3b2fab893f325a9e2b6ef414cdbdfac4326c9ef8e3`.

Text calibration used raw GGUF Qwen2 BPE without the HF tokenizer NFC normalizer. Six decomposed Y-macron occurrences in four corpus lines differ from NFC input; the collected statistics are preserved as observed. Native media prompts used the original HF tokenizer. The ds4 MiMo tokenizer applies NFC.

## Multimodal input contract

Input processing is being aligned with the [SGLang MiMo implementation](https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/multimodal/processors/mimo_v2.py), alongside the pinned checkpoint configuration and tokenizer.

| Input | Required handling | Validation state |
|---|---|---|
| Text | MiMo tokenizer, chat template, and special tokens | Reference text decode passed |
| Image | Production normalization, spatial patch/merge order, vision boundary tokens | Native smoke and one-image GGUF comparison completed; broader checks pending |
| Audio | Original audio tokenizer, local encoder/projector, audio boundary tokens | Native preparation and trunk calibration completed |
| Video | Two-frame temporal patches, MiMo video boundaries, `MM:SS` timestamps | Native temporal preparation and trunk calibration completed |
| Video with audio | Source timing and native audiovisual token layout | Token-layout, audio-coverage and trunk calibration completed |

Generic video ingestion is insufficient here: using independent image frames or generic timestamps changes the model's input contract. Media imatrix collection must consume the correctly prepared original-model embeddings.

## Memory metrics

Exact GGUF file sizes are listed above and in [artifact-manifest.json](MQ-IQ2-XXS-XS-Q8-MM-BF16/artifact-manifest.json). Main tensor payload is **88,771,782,144 bytes**; file sizes additionally include headers, tokenizer metadata and alignment.

Device usage includes KV cache, media activations, allocator overhead, workspaces and the operating system. No context length or concurrency is qualified on DGX Spark. Selective encoder/drafter residency remains an implementation and measurement task.

## Conversion and verification

| Check | Current evidence |
|---|---|
| Source download | All 90 source repository files passed Hub checksum verification |
| MXFP4 repacking and TP=4 QKV ordering | Local numerical checks passed |
| Routed-expert source audit | All 36,096 expert matrices sampled across 108,257 deterministic rows; repacked bytes matched |
| Original-representation reference | [Four shards and media/DFlash assets published and verified](https://huggingface.co/Baekpica/MiMo-V2.6-Flash-RL-GGUF) |
| Reference text smoke | GPU load and arithmetic decode passed |
| Text imatrix | Completed 640 chunks / 655,360 tokens |
| Multimodal imatrix and coverage | Completed 953 records / 464,968 tokens; merged raw sums/counts verified |
| Final mixed tensor inventory and checksums | [508-tensor audit](MQ-IQ2-XXS-XS-Q8-MM-BF16/mixed-artifact-audit.json) passed; six GGUF files listed in SHA256SUMS |
| Embedded MTP and DFlash runtime validation | Pending |
| DGX Spark / ds4-dfm-rs qualification | Integration in progress; full runtime and Spark qualification pending |

The sampled expert audit is not a whole-file byte comparison. A successful reference smoke is not a quality benchmark for the final mixed model. No throughput, accuracy or quality-retention claim is made for the mixed model.

The original-representation reference and its audit are available in the separate [intermediate GGUF repository](https://huggingface.co/Baekpica/MiMo-V2.6-Flash-RL-GGUF).

## Reproduction and release contents

The variant includes four mixed language shards, a BF16/F32 multimodal projector (including input audio-codec tensors), the separate Q8_0 DFlash package and mask embedding, original chat template, tensor recipe, final imatrix, calibration provenance and coverage, conversion scripts, checksums and validation reports.

See [reproduction instructions](MQ-IQ2-XXS-XS-Q8-MM-BF16/reproduction/README.md). The synthesis decoder and training-only audio-codebook statistics are not part of this input-modality projector. No audio-output serving capability is claimed. Original gated source media is not redistributed.

The separate [intermediate repository](https://huggingface.co/Baekpica/MiMo-V2.6-Flash-RL-GGUF) contains the calibration reference. No full Q8_0 or BF16 language baseline was needed.

## Chat template

The upstream [`chat_template.jinja`](chat_template.jinja) is published alongside this card, copied byte for byte from the pinned source revision. Use it with MiMo’s own tokenizer and special-token mapping. Media preprocessing and embedding insertion remain part of the runtime input contract; the template alone does not implement them.

## Runtime support

The current work covers calibration, mixed-quant construction, validation, and a reproducible handoff. MiMo integration into [ds4-dfm-rs](https://github.com/Baekpica/ds4-dfm-rs) and DGX Spark serving tests follow separately. Runnable serving commands will be published after the corresponding runtime path is tested.

## License

MIT, inherited from the [pinned upstream model](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/tree/3b38d063180c3e4aed9691fdc735f3d10b266ee4). Calibration datasets retain their respective licenses and access conditions.
