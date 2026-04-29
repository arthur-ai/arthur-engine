"""Device selection.

`LogisticRegressionModel` and `Classifier` moved to
arthur-engine/models-service/src/models/classifier_arch.py with the rest of
the claim-filter machinery. `get_device` stays here because the relevance
reranker still loads to a torch device on the engine side.
"""

import torch


def get_device(cuda_index: int = 0) -> str:
    return f"cuda:{cuda_index}" if torch.cuda.is_available() else "cpu"
