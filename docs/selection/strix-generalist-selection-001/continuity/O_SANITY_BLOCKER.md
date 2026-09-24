# O: strict JSON sanity failed; panel not admitted

Run: `generalist-selection-001-O-001`, NODE01 + NODE02, original MiMo FP8/MXFP4, TP2, thinking ON. Supervisor dispatch receipt: 2026-09-24T16:12:22+0200, InvocationID `d6b3ceab8b014239888b9f47041646ed`.

Load PASS: 280.514252497 seconds on rank0; actual context 16384, explicit KV 4294967296 bytes/rank, block_size16, num_gpu_blocks11650. This is not a new performance benchmark.

The preflight sanity set ended FAIL at 2026-09-24T16:18:24+0200: five PASS, one FAIL_FORMAT. The JSON request explicitly said `Return only valid JSON with exactly these values: alpha is integer 7 and beta is string "blue".` The response ended naturally after38 native output tokens, far below cap1024, and contains a Markdown-fenced block:

````text
```json
{"alpha": 7, "beta": "blue"}
```
````

The values inside the fence are correct. The returned message as a whole is not the required JSON document. The frozen strict parser rejects the initial backticks. No fence removal, output repair, semantic retry or new model request has been applied. This is a format failure of an admission sanity, not a demonstrated model-runtime corruption, arithmetic failure or general incapacity of the original checkpoint.

Native evidence:

- `requests/preflight__SANITY-json/result.json`: request `generalist-selection-001-O-001/O/preflight/SANITY-json`, input37, output38, natural stop, reasoning boundary closed; record digest `fe7573a91a842096c10458737e6ac35c1b4e3a1b4a53cb9913360e2503bcce0a`.
- `sanity-pre.json`: the independent code_clamp checks all PASS; the other four non-JSON controls PASS.
- `fatal-rank0.json`: preserves the wrapper's broad TECHNICAL_ERROR/SANITY_PREFLIGHT_FAIL label. The concrete interpreted cause is FORMAT_SANITY_ADMISSION_FAILURE, not demonstrated engine corruption.
- The primary raw file contains exactly six preflight records and zero panel records. NODE02's directory contains the same six preflight intent names; no panel intent was present in the readback. Complete peer agreement is checked during CPU delivery.

The preregistered all-six sanity admission gate prevents the twelve panel requests and all engine benchmark requests. Those cases remain NOT_RUN, not twelve semantic failures. The failure is isolated to profile O. Q and D results remain their own previously collected evidence; M retains its separate missing-return sanity failure.

Cleanup/restore was already executing through the original supervisor when this note was created. Its final PASS must be read from `result.json`, `k2-after.json` and the restored owner/unit receipts; it is not inferred here. No further O load, changed sampling, altered schema, runtime repair or extra experiment is authorized by this note.
