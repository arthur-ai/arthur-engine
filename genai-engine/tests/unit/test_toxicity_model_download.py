import pytest

from scorer.checks.toxicity import toxicity
from scorer.checks.toxicity.toxicity import ToxicityScorer


@pytest.mark.unit_tests
def test_download_model_and_tokenizer_builds_classifier(monkeypatch):
    # A scorer created while models were unavailable keeps self.model = None and
    # loads them lazily on the next score() call.
    model, tokenizer, classifier = object(), object(), object()
    monkeypatch.setattr(toxicity, "TOXICITY_MODEL", None)
    monkeypatch.setattr(toxicity, "TOXICITY_TOKENIZER", None)
    monkeypatch.setattr(toxicity, "get_toxicity_model", lambda: model)
    monkeypatch.setattr(toxicity, "get_toxicity_tokenizer", lambda: tokenizer)
    built_with = {}

    def fake_classifier(m, t):
        built_with["args"] = (m, t)
        return classifier

    monkeypatch.setattr(toxicity, "get_toxicity_classifier", fake_classifier)
    profanity = object()
    monkeypatch.setattr(toxicity, "get_profanity_classifier", lambda: profanity)
    scorer = ToxicityScorer.__new__(ToxicityScorer)
    scorer.model = None
    scorer.toxicity_tokenizer = None
    scorer.profanity_classifier = None

    scorer._download_model_and_tokenizer()

    assert built_with["args"] == (model, tokenizer)
    assert scorer.model is classifier
    # score() also needs the tokenizer (chunking) and the profanity classifier.
    assert scorer.toxicity_tokenizer is tokenizer
    assert scorer.profanity_classifier is profanity
