import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import RuleResultEnum, RuleType

from schemas.scorer_schemas import ScoreRequest
from scorer.checks.prompt_injection.classifier import BinaryPromptInjectionClassifier
from scorer.checks.toxicity.toxicity import ToxicityScorer
from utils import model_load

THREADS = 4
CALLS_PER_THREAD = 5


class FakeFastTokenizer:
    """Behaves like a Hugging Face fast tokenizer shared between threads.

    It stores a truncation setting and rewrites it when a call asks for a different
    one; a rewrite while another call is in progress raises "Already borrowed", as
    the real Rust-backed tokenizer does. Calls with the current setting can overlap.
    """

    def __init__(self, truncation: bool | None = None) -> None:
        self.truncation = truncation
        self.calls: list[dict] = []
        self._active = 0
        self._guard = threading.Lock()

    def __call__(self, text: str = "", truncation: bool = False, **kwargs):
        self.calls.append({"truncation": truncation, **kwargs})
        with self._guard:
            if self.truncation != truncation:
                if self._active:
                    raise RuntimeError("Already borrowed")
                self.truncation = truncation
            self._active += 1
        time.sleep(0.005)
        with self._guard:
            self._active -= 1

    def __deepcopy__(self, memo):
        return FakeFastTokenizer(self.truncation)


class FakeChunkIterator:
    def __init__(self, text, tokenizer, *args, **kwargs) -> None:
        tokenizer(text)  # chunkers never truncate
        self._chunks = iter([text])

    def __iter__(self):
        return self._chunks


@pytest.fixture
def fresh_tokenizer_globals(monkeypatch):
    for name in (
        "PROMPT_INJECTION_CHUNKING_TOKENIZER",
        "TOXICITY_CHUNKING_TOKENIZER",
        "PROMPT_INJECTION_CLASSIFIER",
        "TOXICITY_CLASSIFIER",
    ):
        monkeypatch.setattr(model_load, name, None)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "tokenizer_getter,chunking_getter",
    [
        ("get_prompt_injection_tokenizer", "get_prompt_injection_chunking_tokenizer"),
        ("get_toxicity_tokenizer", "get_toxicity_chunking_tokenizer"),
    ],
)
def test_chunking_tokenizer_is_one_separate_copy_without_truncation(
    fresh_tokenizer_globals,
    tokenizer_getter,
    chunking_getter,
):
    shared = FakeFastTokenizer(truncation=True)
    with patch.object(model_load, tokenizer_getter, return_value=shared):
        first = getattr(model_load, chunking_getter)()
        second = getattr(model_load, chunking_getter)()

    assert first is second
    assert first is not shared
    # Set once, at load time, to the setting the chunker always uses
    assert first.truncation is False
    assert len(first.calls) == 1
    assert shared.calls == []


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "classifier_getter,pipeline_factory",
    [
        ("get_prompt_injection_classifier", "TextClassificationPipeline"),
        ("get_toxicity_classifier", "pipeline"),
    ],
)
def test_pipeline_tokenizer_gets_its_truncation_setting_once(
    fresh_tokenizer_globals,
    classifier_getter,
    pipeline_factory,
):
    tokenizer = FakeFastTokenizer()
    model = MagicMock()
    with patch.object(model_load, pipeline_factory) as factory:
        first = getattr(model_load, classifier_getter)(model, tokenizer)
        # The guardrail client and the ML eval scorers both go through this getter
        second = getattr(model_load, classifier_getter)(None, None)

    assert first is second
    factory.assert_called_once()
    assert tokenizer.truncation is True
    assert tokenizer.calls == [{"truncation": True, "max_length": 512}]


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
def test_prompt_injection_chunker_and_pipeline_run_concurrently_without_errors():
    pipeline_tokenizer = FakeFastTokenizer(truncation=True)
    chunking_tokenizer = FakeFastTokenizer(truncation=False)

    def pipeline(chunk):
        pipeline_tokenizer(chunk, truncation=True, max_length=512)
        return [{"label": "SAFE", "score": 0.9}, {"label": "INJECTION", "score": 0.1}]

    classifier = BinaryPromptInjectionClassifier.__new__(
        BinaryPromptInjectionClassifier,
    )
    classifier.tokenizer = pipeline_tokenizer
    classifier.model = pipeline
    classifier.injection_label = "INJECTION"
    request = ScoreRequest(rule_type=RuleType.PROMPT_INJECTION, user_prompt="hello")

    with (
        patch(
            "scorer.checks.prompt_injection.classifier.SlidingWindowChunkIterator",
            FakeChunkIterator,
        ),
        patch(
            "scorer.checks.prompt_injection.classifier.get_prompt_injection_chunking_tokenizer",
            return_value=chunking_tokenizer,
            create=True,
        ),
    ):
        errors = _run_concurrently(lambda: classifier.score(request))

    assert errors == []
    assert pipeline_tokenizer.truncation is True
    assert chunking_tokenizer.truncation is False


@pytest.mark.unit_tests
def test_toxicity_chunker_and_pipeline_run_concurrently_without_errors():
    pipeline_tokenizer = FakeFastTokenizer(truncation=True)
    chunking_tokenizer = FakeFastTokenizer(truncation=False)

    def pipeline(texts, **kwargs):
        pipeline_tokenizer(texts[0], truncation=True, max_length=512)
        return [[{"label": "TOXIC", "score": 0.1}] for _ in texts]

    scorer = ToxicityScorer.__new__(ToxicityScorer)
    scorer.toxicity_tokenizer = pipeline_tokenizer
    scorer.model = pipeline
    scorer.harmfulrequest_classifier = None
    request = ScoreRequest(
        rule_type=RuleType.TOXICITY,
        scoring_text="hello there",
        toxicity_threshold=0.5,
    )

    results = []
    with (
        patch("scorer.checks.toxicity.toxicity.ChunkIterator", FakeChunkIterator),
        patch(
            "scorer.checks.toxicity.toxicity.get_toxicity_chunking_tokenizer",
            return_value=chunking_tokenizer,
            create=True,
        ),
        patch.object(ToxicityScorer, "detect_profanity", return_value=False),
    ):
        errors = _run_concurrently(
            lambda: results.append(scorer.score(request).result),
        )

    assert errors == []
    assert set(results) == {RuleResultEnum.PASS}
