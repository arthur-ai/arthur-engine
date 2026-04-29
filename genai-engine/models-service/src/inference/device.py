"""Device selection.

Migrated from genai-engine/src/utils/classifiers.py:11. Returns a torch
device string suitable for `model.to(...)` / pipeline `device=`.
"""

import torch


def get_device(cuda_index: int = 0) -> str:
    return f"cuda:{cuda_index}" if torch.cuda.is_available() else "cpu"
