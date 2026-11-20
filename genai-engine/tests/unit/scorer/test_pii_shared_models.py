from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.common_schemas import PIIConfig
from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum, RuleType

from rules_engine import RuleEngine
from schemas.scorer_schemas import RuleScore, ScoreRequest
from scorer.checks.pii.classifier import BinaryPIIDataClassifier
from scorer.checks.pii.classifier_v1 import BinaryPIIDataClassifierV1
from utils import model_load

TEXT = "Contact john@example.com today"
EMAIL_START = TEXT.index("john@example.com")
EMAIL_END = EMAIL_START + len("john@example.com")


def _email_span(confidence: float) -> list[dict]:
    return [
        {
            "entity": PIIEntityTypes.EMAIL_ADDRESS.value,
            "span": "john@example.com",
            "start": EMAIL_START,
            "end": EMAIL_END,
            "confidence": confidence,
        },
    ]


@pytest.fixture
def models_enabled(monkeypatch):
    """Load PII models as in production, but with every expensive load mocked."""
    monkeypatch.setattr(model_load, "skip_model_loading", lambda: False)
    monkeypatch.setattr(model_load, "PII_DATE_NLP", None)
    monkeypatch.setattr(model_load, "PII_PRESIDIO_ANALYZER", None)
    with (
        patch.object(model_load.spacy, "load") as spacy_load,
        patch.object(model_load, "AnalyzerEngine") as analyzer_engine,
        patch("scorer.checks.pii.classifier.get_gliner_model", return_value=None),
        patch("scorer.checks.pii.classifier.get_gliner_tokenizer", return_value=None),
        patch("scorer.checks.pii.classifier_v1.get_gliner_model", return_value=None),
        patch(
            "scorer.checks.pii.classifier_v1.get_gliner_tokenizer",
            return_value=None,
        ),
    ):
        yield spacy_load, analyzer_engine


@pytest.mark.unit_tests
def test_classifiers_share_one_spacy_date_pipeline(models_enabled):
    spacy_load, _ = models_enabled

    first = BinaryPIIDataClassifier()
    second = BinaryPIIDataClassifier()

    assert first.date_nlp is second.date_nlp
    spacy_load.assert_called_once_with("en_core_web_lg", exclude=["ner"])
    # add_pipe on the shared pipeline must not run again for the second classifier
    spacy_load.return_value.add_pipe.assert_called_once_with("find_dates")


@pytest.mark.unit_tests
def test_v1_classifiers_share_one_presidio_analyzer(models_enabled):
    _, analyzer_engine = models_enabled

    first = BinaryPIIDataClassifierV1()
    second = BinaryPIIDataClassifierV1()

    assert first.analyzer is second.analyzer
    analyzer_engine.assert_called_once_with()


@pytest.mark.unit_tests
def test_skip_mode_loads_no_spacy_pipeline_and_still_scores(monkeypatch):
    monkeypatch.setattr(model_load, "skip_model_loading", lambda: True)
    monkeypatch.setattr(model_load, "PII_DATE_NLP", None)
    with patch.object(model_load.spacy, "load") as spacy_load:
        assert model_load.get_pii_date_nlp() is None
        classifier = BinaryPIIDataClassifier()
        result = classifier.score(
            ScoreRequest(rule_type=RuleType.PII_DATA, scoring_text="See you Monday"),
        )

    spacy_load.assert_not_called()
    assert classifier.date_nlp is None
    assert result.result in (RuleResultEnum.PASS, RuleResultEnum.FAIL)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "classifier_class,module",
    [
        (BinaryPIIDataClassifier, "scorer.checks.pii.classifier"),
        (BinaryPIIDataClassifierV1, "scorer.checks.pii.classifier_v1"),
    ],
)
@pytest.mark.parametrize(
    "threshold,confidence,expected",
    [
        # No threshold: the 0.5 default drops a 0.3 detection, keeps a 0.6 one
        (None, 0.3, RuleResultEnum.PASS),
        (None, 0.6, RuleResultEnum.FAIL),
        # An explicit 0.0 keeps every detection instead of falling back to 0.5
        (0.0, 0.3, RuleResultEnum.FAIL),
        (0.8, 0.6, RuleResultEnum.PASS),
        (0.8, 0.9, RuleResultEnum.FAIL),
    ],
)
def test_pii_confidence_threshold(
    models_enabled,
    classifier_class,
    module,
    threshold,
    confidence,
    expected,
):
    classifier = classifier_class()
    with patch(f"{module}.process_presidio", return_value=_email_span(confidence)):
        result = classifier.score(
            ScoreRequest(
                rule_type=RuleType.PII_DATA,
                scoring_text=TEXT,
                pii_confidence_threshold=threshold,
            ),
        )

    assert result.result == expected


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "use_v2,rule_threshold,sent_threshold",
    [
        # A rule with no threshold reads back as 0: V2 applies its own default
        # (0.5) as before, and V1 keeps filtering at 0 as before.
        (True, None, None),
        (False, None, 0.0),
        (True, 0.7, 0.7),
        (False, 0.7, 0.7),
    ],
)
def test_pii_rule_without_threshold_keeps_each_classifiers_default(
    monkeypatch,
    use_v2,
    rule_threshold,
    sent_threshold,
):
    monkeypatch.setattr(model_load, "USE_PII_MODEL_V2", use_v2)
    config = (
        PIIConfig()
        if rule_threshold is None
        else PIIConfig(confidence_threshold=rule_threshold)
    )
    rule = MagicMock()
    rule.get_pii_config.return_value = config
    request = MagicMock()
    request.get_scoring_text.return_value = TEXT
    engine = RuleEngine.__new__(RuleEngine)
    engine.scorer = MagicMock()
    engine.scorer.score.return_value = RuleScore(
        result=RuleResultEnum.PASS,
        prompt_tokens=0,
        completion_tokens=0,
    )
    engine.token_counter = MagicMock()

    engine.run_pii_data_rule(request, rule)

    score_request = engine.scorer.score.call_args.args[0]
    assert score_request.pii_confidence_threshold == sent_threshold
