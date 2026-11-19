import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import RuleResultEnum

from schemas.scorer_schemas import RuleScore
from scorer.checks.pii import classifier as pii_classifier_module
from scorer.checks.pii import classifier_v1 as pii_classifier_v1_module
from scorer.checks.pii.classifier import BinaryPIIDataClassifier
from scorer.checks.pii.classifier_v1 import BinaryPIIDataClassifierV1
from scorer.ml_scorers import ToxicityMLScorer, run_ml_scorer
from utils import constants

PASS_SCORE = RuleScore(
    result=RuleResultEnum.PASS,
    prompt_tokens=0,
    completion_tokens=0,
)


@pytest.fixture(autouse=True)
def fresh_pii_classifiers(monkeypatch):
    """Start every test with no cached PII classifier in this process."""
    monkeypatch.setattr(pii_classifier_module, "_PII_CLASSIFIER", None, raising=False)
    monkeypatch.setattr(
        pii_classifier_v1_module,
        "_PII_CLASSIFIER_V1",
        None,
        raising=False,
    )


def _count_constructions(classifier_class, delay: float = 0.0):
    """Patch a classifier so building it is free and counted instead of loading models."""
    constructions = []

    def fake_init(self):
        constructions.append(self)
        time.sleep(delay)

    return constructions, (
        patch.object(classifier_class, "__init__", fake_init),
        patch.object(classifier_class, "score", return_value=PASS_SCORE),
    )


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "eval_type,classifier_class",
    [("pii", BinaryPIIDataClassifier), ("pii_v1", BinaryPIIDataClassifierV1)],
)
def test_pii_ml_evals_build_the_classifier_once(eval_type, classifier_class):
    # Building a PII classifier loads a spaCy pipeline (~0.6 GB); doing it per eval
    # grows the worker until it is killed, so every eval must reuse one instance.
    constructions, (init_patch, score_patch) = _count_constructions(classifier_class)
    with init_patch, score_patch:
        for _ in range(5):
            result = run_ml_scorer(eval_type, "no pii here", {})
            assert result.score == 1

    assert len(constructions) == 1


@pytest.mark.unit_tests
def test_concurrent_pii_ml_evals_share_one_classifier():
    # Continuous evals run on several threads; the first wave must not each build one.
    constructions, (init_patch, score_patch) = _count_constructions(
        BinaryPIIDataClassifier,
        delay=0.05,
    )
    start = threading.Barrier(8)
    errors = []

    def run_eval():
        try:
            start.wait()
            run_ml_scorer("pii", "no pii here", {})
        except Exception as e:  # pragma: no cover - surfaced by the assert below
            errors.append(e)

    with init_patch, score_patch:
        threads = [threading.Thread(target=run_eval) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert errors == []
    assert len(constructions) == 1


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "config,expected_threshold",
    [
        ({}, constants.DEFAULT_TOXICITY_RULE_THRESHOLD),
        ({"toxicity_threshold": None}, constants.DEFAULT_TOXICITY_RULE_THRESHOLD),
        ({"toxicity_threshold": 0.8}, 0.8),
        ({"toxicity_threshold": 0.0}, 0.0),
    ],
)
def test_toxicity_ml_eval_threshold_defaults_like_the_guardrail(
    config,
    expected_threshold,
):
    # Without a threshold the toxicity scorer skips the check, and a skip is
    # reported as a failed eval, so fall back to the guardrail rule's default.
    scorer = MagicMock()
    scorer.score.return_value = PASS_SCORE

    result = ToxicityMLScorer(scorer).run("hello there", config)

    request = scorer.score.call_args.args[0]
    assert request.toxicity_threshold == expected_threshold
    assert result.score == 1
