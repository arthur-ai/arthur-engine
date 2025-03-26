import logging

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger()


def get_device(cuda_index: int = 0):
    return f"cuda:{cuda_index}" if torch.cuda.is_available() else "cpu"


class LogisticRegressionModel(torch.nn.Module):
    def __init__(self, input_size, num_classes=2):
        """
        Logistic Regression model for both binary and multi-class classification.

        Args:
            input_size (int): Number of input features.
            num_classes (int): Number of output classes. Default is 2 for binary classification.
        """
        super(LogisticRegressionModel, self).__init__()
        self.num_classes = num_classes
        self.linear = torch.nn.Linear(input_size, num_classes if num_classes > 2 else 1)

    def forward(self, x):
        """
        Forward pass for the model.

        Args:
            x (torch.Tensor): Input tensor of shape (batch_size, input_size).

        Returns:
            torch.Tensor: Predicted logits or probabilities based on context.
        """
        logits = self.linear(x)  # Raw scores (logits)

        if self.num_classes == 2:
            probs = torch.sigmoid(logits)
        else:
            probs = torch.nn.functional.softmax(logits, dim=-1)

        return probs


class Classifier(torch.nn.Module):
    """
    SetFit text classifier on a pretrained sentence-transformer
    https://arxiv.org/abs/2209.11055
    """

    def __init__(
        self,
        transformer_model: SentenceTransformer,
        classifier: LogisticRegressionModel,
        label_map=None,
    ):
        super(Classifier, self).__init__()
        self.transformer = transformer_model
        self.classifier = classifier.to(get_device()).to(torch.float64)
        self.label_map = label_map
        if label_map is not None:
            self.inv_label_map = {v: k for k, v in label_map.items()}

    @classmethod
    def from_pickled_classifier(
        cls,
        embedding_model_name_or_path: str,
        classifier: LogisticRegressionModel,
        use_local_files=True,
        label_map=None,
    ):
        if use_local_files:
            logger.info(
                f"Loading model from local files @ {embedding_model_name_or_path}",
            )
        else:
            logger.info(
                f"Loading model {embedding_model_name_or_path} from remote HF hub",
            )

        t = SentenceTransformer(
            embedding_model_name_or_path,
            device=torch.device(get_device()),
        )

        return cls(t, classifier=classifier, label_map=label_map)

    def forward(self, texts):
        embeddings: torch.Tensor = torch.tensor(
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
            res = {"label": label, "logit": logit, "prob": logit}

        else:
            logits = self.classifier(embeddings).detach().cpu().numpy()
            label = np.argmax(np.log(logits), axis=1)
            res = {"label": label, "logit": np.log(logits), "prob": logits}
        if self.label_map is not None:
            res["pred_label_str"] = [self.inv_label_map[x] for x in res["label"]]
        return res
