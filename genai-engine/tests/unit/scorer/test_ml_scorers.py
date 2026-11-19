from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import RuleResultEnum

from schemas.scorer_schemas import RuleScore
from scorer.checks.pii.classifier import BinaryPIIDataClassifier
from scorer.ml_scorers import ToxicityMLScorer, run_ml_scorer
from utils import constants, model_load

PASS_SCORE = RuleScore(
    result=RuleResultEnum.PASS,
    prompt_tokens=0,
    completion_tokens=0,
)


@pytest.mark.unit_tests
def test_pii_ml_evals_load_the_spacy_pipeline_once(monkeypatch):
    # Each PII ML eval builds a classifier. The spaCy pipeline it uses (~0.6 GB)
    # must be loaded once per process, or every eval grows the worker until it
    # is killed.
    monkeypatch.setattr(model_load, "PII_DATE_NLP", None)
    monkeypatch.setattr(model_load, "skip_model_loading", lambda: False)
    with (
        patch("scorer.checks.pii.classifier.get_gliner_model", return_value=None),
        patch("scorer.checks.pii.classifier.get_gliner_tokenizer", return_value=None),
        patch("scorer.checks.pii.classifier.get_presidio_analyzer", return_value=None),
        patch.object(model_load.spacy, "load") as spacy_load,
        patch.object(BinaryPIIDataClassifier, "score", return_value=PASS_SCORE),
    ):
        for _ in range(5):
            result = run_ml_scorer("pii", "no pii here", {})
            assert result.score == 1

    spacy_load.assert_called_once_with("en_core_web_lg", exclude=["ner"])
    spacy_load.return_value.add_pipe.assert_called_once_with("find_dates")


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
