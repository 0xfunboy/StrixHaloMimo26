from __future__ import annotations

import torch


def _requantize_fp8(
    grouped: torch.Tensor,
    rows_rank: int,
    block: int,
    dtype: torch.dtype,
) -> tuple[torch.Tensor, torch.Tensor]:
    from vllm.model_executor.layers.quantization.utils.quant_utils import (
        GroupShape,
        scaled_quantize,
    )

    padded = ((rows_rank + block - 1) // block) * block
    if padded != rows_rank:
        grouped = torch.cat(
            [grouped, grouped.new_zeros(padded - rows_rank, grouped.shape[1])],
            dim=0,
        )
    w_rank, s_rank = scaled_quantize(
        grouped,
        GroupShape(block, block),
        dtype,
        compute_dtype=torch.float32,
    )
    return w_rank[:rows_rank], s_rank


def _mimo26_shard_fp8_qkv_proj(
    w_full: torch.Tensor,
    s_full: torch.Tensor,
    num_heads: int,
    num_kv_heads: int,
    head_dim: int,
    v_head_dim: int,
    tp_rank: int,
    tp_size: int,
    block: int = 128,
    ckpt_tp: int = 4,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Backport vLLM #57508 for MiMo-V2.6 Flash.

    The V2.6 fused FP8 QKV checkpoint is exported as ckpt_tp independent
    chunks. Each chunk is laid out [Q_c | K_c | V_c] and has its own
    block-scale grid. For this Xiaomi Flash checkpoint ckpt_tp is 4,
    matching the text config base num_key_value_heads; SWA layers still
    use 8 KV heads but remain stored in four export chunks.

    This function intentionally keeps the installed vLLM call signature so
    the old loader can be monkey-patched without modifying site-packages.
    """
    if num_heads % tp_size:
        raise ValueError(
            f"num_heads={num_heads} must be divisible by tp_size={tp_size}"
        )
    if ckpt_tp <= 0 or num_heads % ckpt_tp or num_kv_heads % ckpt_tp:
        raise ValueError(
            f"checkpoint TP={ckpt_tp} does not divide heads: "
            f"num_heads={num_heads}, num_kv_heads={num_kv_heads}"
        )

    if tp_size <= num_kv_heads:
        if num_kv_heads % tp_size:
            raise ValueError(
                f"num_kv_heads={num_kv_heads} must divide tp_size={tp_size}"
            )
        kv_head_ids = list(
            range(
                tp_rank * (num_kv_heads // tp_size),
                (tp_rank + 1) * (num_kv_heads // tp_size),
            )
        )
    else:
        if tp_size % num_kv_heads:
            raise ValueError(
                f"tp_size={tp_size} must be divisible by "
                f"num_kv_heads={num_kv_heads}"
            )
        kv_head_ids = [tp_rank // (tp_size // num_kv_heads)]

    q_head_ids = list(
        range(
            tp_rank * (num_heads // tp_size),
            (tp_rank + 1) * (num_heads // tp_size),
        )
    )

    if w_full.shape[0] % ckpt_tp:
        raise ValueError(
            f"fused qkv rows={w_full.shape[0]} not divisible by ckpt_tp={ckpt_tp}"
        )
    rows_per_chunk = w_full.shape[0] // ckpt_tp
    q_per_chunk = (num_heads // ckpt_tp) * head_dim
    k_per_chunk = (num_kv_heads // ckpt_tp) * head_dim
    v_per_chunk = (num_kv_heads // ckpt_tp) * v_head_dim
    if q_per_chunk + k_per_chunk + v_per_chunk != rows_per_chunk:
        raise ValueError(
            "MiMo-V2.6 fused QKV chunk geometry mismatch: "
            f"rows={rows_per_chunk}, q={q_per_chunk}, "
            f"k={k_per_chunk}, v={v_per_chunk}"
        )

    chunk_scale_rows = (rows_per_chunk + block - 1) // block
    rows = torch.arange(w_full.shape[0], device="cpu")
    per_chunk_scales = s_full.shape[0] == ckpt_tp * chunk_scale_rows
    if per_chunk_scales:
        scale_index = (
            (rows // rows_per_chunk) * chunk_scale_rows
            + (rows % rows_per_chunk) // block
        )
    elif s_full.shape[0] == (w_full.shape[0] + block - 1) // block:
        scale_index = rows // block
    else:
        raise ValueError(
            f"fused qkv scale rows={s_full.shape[0]}, expected "
            f"{ckpt_tp * chunk_scale_rows} per-chunk or "
            f"{(w_full.shape[0] + block - 1) // block} continuous"
        )

    if tp_size == ckpt_tp and per_chunk_scales:
        return (
            w_full.chunk(ckpt_tp, dim=0)[tp_rank],
            s_full.chunk(ckpt_tp, dim=0)[tp_rank],
        )

    q_heads_per_chunk = num_heads // ckpt_tp
    kv_heads_per_chunk = num_kv_heads // ckpt_tp
    head_rows = torch.arange(head_dim)
    v_head_rows = torch.arange(v_head_dim)
    row_index: list[torch.Tensor] = []

    for head in q_head_ids:
        chunk = head // q_heads_per_chunk
        row_index.append(
            chunk * rows_per_chunk
            + (head % q_heads_per_chunk) * head_dim
            + head_rows
        )
    for head in kv_head_ids:
        chunk = head // kv_heads_per_chunk
        row_index.append(
            chunk * rows_per_chunk
            + q_per_chunk
            + (head % kv_heads_per_chunk) * head_dim
            + head_rows
        )
    for head in kv_head_ids:
        chunk = head // kv_heads_per_chunk
        row_index.append(
            chunk * rows_per_chunk
            + q_per_chunk
            + k_per_chunk
            + (head % kv_heads_per_chunk) * v_head_dim
            + v_head_rows
        )

    index = torch.cat(row_index)
    grouped = w_full[index].to(torch.float32) * s_full[
        scale_index[index]
    ].repeat_interleave(block, dim=1)
    return _requantize_fp8(grouped, index.numel(), block, w_full.dtype)


def apply_mimo26_vllm_patches() -> None:
    import vllm.model_executor.models.mimo_v2 as mimo_v2

    if getattr(mimo_v2, "_mimo26_qkv_patch_applied", False):
        return
    mimo_v2._shard_fp8_qkv_proj = _mimo26_shard_fp8_qkv_proj
    mimo_v2._mimo26_qkv_patch_applied = True
    mimo_v2._mimo26_qkv_patch_source = "vllm-57508-backport-ckpt-tp4"
