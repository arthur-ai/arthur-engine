"""Torch nn modules for the claim classifier.

Migrated from genai-engine/src/utils/classifiers.py. These are the
architectures that the .pth weights at
inference/claim_filter/claim_classifier/*.pth load into.

LogisticRegressionModel: standalone logistic-regression head (binary or
multi-class), used as the classifier head over sentence embeddings.

Classifier: SetFit-style wrapper that combines a SentenceTransformer encoder
with a LogisticRegressionModel head. forward(texts) returns a dict with
`label` (argmax indices), `logit`, `prob` (softmax distribution), and
`pred_label_str` (label_map applied) — matching the shape the engine code
used to consume.
"""

import logging
from typing import Any

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from inference.device import get_device

logger = logging.getLogger(__name__)


class LogisticRegressionModel(torch.nn.Module):
    def __init__(self, input_size: int, num_classes: int = 2) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.linear = torch.nn.Linear(input_size, num_classes if num_classes > 2 else 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.linear(x)
        if self.num_classes == 2:
            return torch.sigmoid(logits)
        return torch.nn.functional.softmax(logits, dim=-1)


class Classifier(torch.nn.Module):
    """SetFit-style text classifier: sentence embeddings → logreg head.

    https://arxiv.org/abs/2209.11055
    """

    def __init__(
        self,
        transformer_model: SentenceTransformer,
        classifier: LogisticRegressionModel,
        label_map: dict[str, int] | None = None,
    ) -> None:
        super().__init__()
        self.transformer = transformer_model
        self.classifier = classifier.to(get_device()).to(torch.float64)
        self.label_map = label_map
        if label_map is not None:
            self.inv_label_map = {v: k for k, v in label_map.items()}

    def forward(self, texts: list[str]) -> dict[str, Any]:
        with torch.no_grad():
            embeddings = torch.tensor(
                self.transformer.encode(
                    texts,
                    convert_to_tensor=True,
                    batch_size=len(texts),
                ).to(get_device()),
                dtype=torch.float64,
            )
            if self.classifier.num_classes == 2:
                logit = self.classifier(embeddings).view(-1).detach().cpu().numpy()
                label = (logit > 0.5).astype(int)
                res: dict[str, Any] = {"label": label, "logit": logit, "prob": logit}
            else:
                logits = self.classifier(embeddings).detach().cpu().numpy()
                label = np.argmax(np.log(logits), axis=1)
                res = {"label": label, "logit": np.log(logits), "prob": logits}
            if self.label_map is not None:
                res["pred_label_str"] = [self.inv_label_map[x] for x in res["label"]]
            return res
