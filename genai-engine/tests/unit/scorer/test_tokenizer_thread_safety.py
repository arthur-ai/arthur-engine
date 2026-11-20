import threading
import time
from unittest.mock import patch

import pytest
from arthur_common.models.enums import RuleResultEnum, RuleType

from schemas.scorer_schemas import ScoreRequest
from scorer.checks.prompt_injection.classifier import BinaryPromptInjectionClassifier
from scorer.checks.toxicity.toxicity import ToxicityScorer

THREADS = 4
CALLS_PER_THREAD = 5


class SharedTokenizer:
    """Stands in for a Hugging Face fast tokenizer shared by a chunker and a pipeline.

    The real one raises "Already borrowed" when one thread changes its truncation
    setting while another thread is using it; this one raises whenever two calls
    overlap, which is what the scorers must prevent.
    """

    def __init__(self) -> None:
        self._active = 0
        self._guard = threading.Lock()

    def use(self) -> None:
        with self._guard:
            if self._active:
                raise RuntimeError("Already borrowed")
            self._active += 1
        time.sleep(0.005)
        with self._guard:
            self._active -= 1


class FakeChunkIterator:
    def __init__(self, text, tokenizer, *args, **kwargs) -> None:
        tokenizer.use()
        self._chunks = iter([text])

    def __iter__(self):
        return self._chunks


def _run_concurrently(score) -> list[Exception]:
    errors: list[Exception] = []
    start = threading.Barrier(THREADS)

    def work() -> None:
        start.wait()
        for _ in range(CALLS_PER_THREAD):
            try:
                score()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=work) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return errors


@pytest.mark.unit_tests
def test_prompt_injection_scorer_serialises_its_shared_tokenizer():
    tokenizer = SharedTokenizer()

    def pipeline(chunk):
        tokenizer.use()
        return [{"label": "SAFE", "score": 0.9}, {"label": "INJECTION", "score": 0.1}]

    classifier = BinaryPromptInjectionClassifier.__new__(
        BinaryPromptInjectionClassifier,
    )
    classifier.tokenizer = tokenizer
    classifier.model = pipeline
    classifier.injection_label = "INJECTION"
    request = ScoreRequest(rule_type=RuleType.PROMPT_INJECTION, user_prompt="hello")

    with patch(
        "scorer.checks.prompt_injection.classifier.SlidingWindowChunkIterator",
        FakeChunkIterator,
    ):
        errors = _run_concurrently(lambda: classifier.score(request))

    assert errors == []


@pytest.mark.unit_tests
def test_toxicity_scorer_serialises_its_shared_tokenizer():
    tokenizer = SharedTokenizer()

    def pipeline(texts, **kwargs):
        tokenizer.use()
        return [[{"label": "TOXIC", "score": 0.1}] for _ in texts]

    scorer = ToxicityScorer.__new__(ToxicityScorer)
    scorer.toxicity_tokenizer = tokenizer
    scorer.model = pipeline
    scorer.harmfulrequest_classifier = None
    request = ScoreRequest(
        rule_type=RuleType.TOXICITY,
        scoring_text="hello there",
        toxicity_threshold=0.5,
    )

    with (
        patch("scorer.checks.toxicity.toxicity.ChunkIterator", FakeChunkIterator),
        patch.object(ToxicityScorer, "detect_profanity", return_value=False),
    ):
        results = []
        errors = _run_concurrently(
            lambda: results.append(scorer.score(request).result),
        )

    assert errors == []
    assert set(results) == {RuleResultEnum.PASS}
