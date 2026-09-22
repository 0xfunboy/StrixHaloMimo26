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
    """Historical r6 regression: WRONG global [Q|K|V] interpretation.

    Preserved only as a negative test.  It assumes one global scale grid and a
    globally contiguous Q block followed by K and V, which contradicts the
    ckpt_tp=4 per-chunk export verified by vLLM #57508.
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
            f"geometry mismatch: weight_rows={w_full.shape[0]} expected={expected_rows}"
        )

    scale_rows = (w_full.shape[0] + block - 1) // block
    scale_cols = (w_full.shape[1] + block - 1) // block
    if s_full.shape[0] < scale_rows or s_full.shape[1] < scale_cols:
        raise ValueError("scale grid too small")
    s_grid = s_full[:scale_rows, :scale_cols].contiguous()

    if tp_size == 1:
        return w_full, s_grid

    w_dequant = scaled_dequantize(
        w_full,
        s_grid,
        GroupShape(block, block),
        out_dtype=torch.float32,
    )

    q = w_dequant[:q_rows]
    k = w_dequant[q_rows:q_rows + k_rows]
    v = w_dequant[q_rows + k_rows:]

    q_local = q.chunk(tp_size, dim=0)[tp_rank].contiguous()
    k_local = k.chunk(tp_size, dim=0)[tp_rank].contiguous()
    v_local = v.chunk(tp_size, dim=0)[tp_rank].contiguous()
    local = torch.cat((q_local, k_local, v_local), dim=0).contiguous()

    if local.shape[0] % block != 0:
        raise ValueError(
            f"TP-local rows must align to {block}: {local.shape[0]}"
        )

    return scaled_quantize(
        local,
        GroupShape(block, block),
        w_full.dtype,
        compute_dtype=torch.float32,
    )
