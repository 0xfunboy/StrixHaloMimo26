# Reproduction

These are the conversion/calibration scripts used on the B300 development host.
The original-representation model is about175 GB and is not a one-Spark model.
Pin llama.cpp using toolchain-pins.json and retain the base model revision.

To reproduce quantization without rerunning calibration, download the four
MXFP4-BF16 reference shards from Baekpica/MiMo-V2.6-Flash-RL-GGUF and use the
published calibration/imatrix.gguf plus tensor-types.txt. The command is:

```bash
llama-quantize --pure --allow-requantize --keep-split \
  --imatrix calibration/imatrix.gguf \
  --tensor-type-file tensor-types.txt \
  --token-embedding-type q8_0 --output-tensor-type q8_0 \
  reference/MiMo-V2.6-Flash-RL-MXFP4-BF16-00001-of-00004.gguf \
  MiMo-V2.6-Flash-RL-MQ-IQ2-XXS-XS-Q8.gguf IQ2_XXS 18
```

The recipe uses exact per-tensor assignments. The bulk file-type label is
IQ2_XXS, while dense matrices and embedded MTP remain Q8_0. This command
reproduces tensor targets; the release also overrides display name/description.

For a full calibration rebuild, scripts use /root/mimo-work/{source,reference,
handoff,artifacts}. Restore the pinned source with download_source.sh, copy
reference-code/sglang-*.py to reference/, and use calibration/sources.json for
pinned dataset files. Original source media is not redistributed in this model
repository. The private Spark handoff retains the prepared media and native
embedding fixtures. The scripts may be relocated consistently; keep hashes and
source revisions. Text calibration used raw Qwen2 BPE input without HF NFC
normalization; six decomposed Y-macron occurrences in four lines differ. See
text-normalization-audit.json. Native media used the original HF tokenizer.
Rebuild compiled tools on aarch64 rather than reusing the
x86_64 development binaries. SGLang reference files retain Apache-2.0; llama.cpp
uses its included MIT license. Dataset attribution remains under calibration/.
