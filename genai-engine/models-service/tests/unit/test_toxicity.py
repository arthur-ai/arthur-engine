"""Toxicity inference tests — needs real models.

Migrated from genai-engine/tests/unit/test_toxicity.py with the same toxic /
non-toxic samples but calling `inference.toxicity.classify(ToxicityRequest)`
directly. Profanity-blacklist regex is testable without weights.
"""

import os

import pytest

from inference.toxicity import classify
from inference.toxicity.profanity import detect_profanity
from schemas import InferenceResult, ToxicityRequest, ToxicityViolationType

__location__ = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.unit_tests
def test_profanity_regex_matches():
    assert detect_profanity("shit") is not None
    assert detect_profanity("fuck") is not None
    assert detect_profanity("f*ck") is not None
    assert detect_profanity("a55") is not None
    # Spaced-out forms shouldn't match the obscured-regex.
    assert detect_profanity("s h i t") is None
    assert detect_profanity("distinguish it") is None
    assert detect_profanity("get it") is None


@pytest.mark.real_models
def test_non_toxic_passes():
    req = ToxicityRequest(text="This is a normal sentence without any code.", threshold=0.5)
    result = classify(req)
    assert result.result == InferenceResult.PASS
    assert result.violation_type == ToxicityViolationType.BENIGN


@pytest.mark.real_models
@pytest.mark.parametrize(
    "text",
    [
        "You should know women's sports can kiss my ass lol",
        "Women deserve to be abused, I guess.",
        "Time to nuke China or Unleash a plague.",
        "Stupid ugly asian tan ass snitch",
        "LGBTQ+ are mentally ill. Period.",
    ],
)
def test_toxic_text_is_flagged(text):
    req = ToxicityRequest(text=text, threshold=0.35)
    result = classify(req)
    assert result.result == InferenceResult.FAIL
    assert result.violation_type != ToxicityViolationType.BENIGN


@pytest.mark.real_models
def test_profanity_short_circuits():
    """When the regex blacklist hits, we should report PROFANITY without
    consulting the toxicity classifier."""
    req = ToxicityRequest(text="that is some shit you wrote", threshold=0.5)
    result = classify(req)
    assert result.result == InferenceResult.FAIL
    assert result.profanity_detected
    assert result.violation_type == ToxicityViolationType.PROFANITY


@pytest.mark.real_models
def test_empty_text_passes():
    req = ToxicityRequest(text="", threshold=0.5)
    result = classify(req)
    assert result.result == InferenceResult.PASS


@pytest.mark.unit_tests
def test_real_world_corpus():
    """If the not-toxic fixture is shipped, smoke-test it. Otherwise skip."""
    fixture = os.path.join(__location__, "fixtures", "sampled_nottoxic.txt")
    if not os.path.exists(fixture):
        pytest.skip(f"Fixture not present at {fixture}")
    # When fixture is present the test is real-models territory; skip in
    # unit-test mode by leaving real evaluation to the model_models marker.
