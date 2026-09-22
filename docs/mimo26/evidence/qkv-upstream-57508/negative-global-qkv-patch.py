from __future__ import annotations

import torch


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
) -> tuple[torch.Tensor, torch.Tensor]:
    """Shard MiMo-V2.6 fused FP8 QKV across TP ranks.

    MiMo-V2.6 stores fused qkv_proj in the same order used by its official
    forward path: one contiguous Q block, followed by K, followed by V:

        [Q_all_heads | K_all_kv_heads | V_all_kv_heads]

    The FP8 block scale grid belongs to this full fused matrix and can include
    global row padding. It must not be split into per-KV-head groups.

    We therefore dequantize the complete fused tensor with its original
    128x128 scale grid, shard Q/K/V independently by their head dimensions,
    concatenate the local rank layout expected by QKVParallelLinear, and
    requantize to the same block-FP8 format.
    """
    from vllm.model_executor.layers.quantization.utils.quant_utils import (
        GroupShape,
        scaled_dequantize,
        scaled_quantize,
    )

    assert w_full.ndim == 2 and s_full.ndim == 2
    assert w_full.dtype == torch.float8_e4m3fn
    assert num_heads % tp_size == 0
    assert num_kv_heads % tp_size == 0
    assert w_full.shape[1] % block == 0

    q_rows = num_heads * head_dim
    k_rows = num_kv_heads * head_dim
    v_rows = num_kv_heads * v_head_dim
    expected_rows = q_rows + k_rows + v_rows
    if w_full.shape[0] != expected_rows:
        raise ValueError(
            "MiMo-V2.6 fused QKV geometry mismatch: "
            f"weight_rows={w_full.shape[0]} expected={expected_rows} "
            f"q={q_rows} k={k_rows} v={v_rows}"
        )

    scale_rows = (w_full.shape[0] + block - 1) // block
    scale_cols = (w_full.shape[1] + block - 1) // block
    if s_full.shape[0] < scale_rows or s_full.shape[1] < scale_cols:
        raise ValueError(
            f"MiMo-V2.6 QKV scale grid too small: weight={tuple(w_full.shape)} "
            f"scale={tuple(s_full.shape)} need=({scale_rows},{scale_cols})"
        )
    s_grid = s_full[:scale_rows, :scale_cols].contiguous()

    # Pipeline-parallel / TP=1 needs no QKV transformation at all. Preserve
    # checkpoint FP8 bits exactly; only remove global scale padding that does
    # not correspond to real weight rows.
    if tp_size == 1:
        return w_full, s_grid

    w_dequant = scaled_dequantize(
        w_full,
        s_grid,
        GroupShape(block, block),
        out_dtype=torch.float32,
    )

    q = w_dequant[:q_rows]
    k = w_dequant[q_rows : q_rows + k_rows]
    v = w_dequant[q_rows + k_rows :]

    q_local = q.chunk(tp_size, dim=0)[tp_rank].contiguous()
    k_local = k.chunk(tp_size, dim=0)[tp_rank].contiguous()
    v_local = v.chunk(tp_size, dim=0)[tp_rank].contiguous()
    local = torch.cat((q_local, k_local, v_local), dim=0).contiguous()

    if local.shape[0] % block != 0:
        raise ValueError(
            f"MiMo-V2.6 TP-local QKV rows must align to {block}: "
            f"{local.shape[0]}"
        )

    return scaled_quantize(
        local,
        GroupShape(block, block),
        w_full.dtype,
        compute_dtype=torch.float32,
    )


def apply_mimo26_vllm_patches() -> None:
    import vllm.model_executor.models.mimo_v2 as mimo_v2

    if getattr(mimo_v2, "_mimo26_qkv_patch_applied", False):
        return
    mimo_v2._shard_fp8_qkv_proj = _mimo26_shard_fp8_qkv_proj
    mimo_v2._mimo26_qkv_patch_applied = True