import threading
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import RuleResultEnum, RuleType

from schemas.scorer_schemas import ScoreRequest
from scorer.checks.prompt_injection.classifier import BinaryPromptInjectionClassifier
from scorer.checks.toxicity.toxicity import ToxicityScorer
from utils import model_load


class HoldFirstChunkerCall:
    """Keeps the first chunker tokenizer call in progress until released.

    This forces the overlap the race needs instead of hoping thread scheduling
    produces it: while one score() is inside its chunker's tokenizer call, a second
    score() runs its chunker and pipeline end to end.
    """

    def __init__(self) -> None:
        self.held = threading.Event()
        self.release = threading.Event()
        self._taken = False
        self._lock = threading.Lock()

    def maybe_hold(self, truncation: bool) -> None:
        if truncation:
            return
        with self._lock:
            if self._taken:
                return
            self._taken = True
        self.held.set()
        self.release.wait(timeout=5)


class FakeFastTokenizer:
    """Behaves like a Hugging Face fast tokenizer shared between threads.

    It stores a truncation setting and rewrites it when a call asks for a different
    one; a rewrite while another call is in progress raises "Already borrowed", as
    the real Rust-backed tokenizer does. Calls with the current setting can overlap.
    """

    def __init__(
        self,
        truncation: bool | None = None,
        gate: HoldFirstChunkerCall | None = None,
    ) -> None:
        self.truncation = truncation
        self.gate = gate
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
        if self.gate:
            self.gate.maybe_hold(truncation)
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
    "classifier_getter,pipeline_factory,model_getter,tokenizer_getter",
    [
        (
            "get_prompt_injection_classifier",
            "TextClassificationPipeline",
            "get_prompt_injection_model",
            "get_prompt_injection_tokenizer",
        ),
        (
            "get_toxicity_classifier",
            "pipeline",
            "get_toxicity_model",
            "get_toxicity_tokenizer",
        ),
    ],
)
def test_pipeline_tokenizer_gets_its_truncation_setting_once(
    fresh_tokenizer_globals,
    classifier_getter,
    pipeline_factory,
    model_getter,
    tokenizer_getter,
):
    tokenizer = FakeFastTokenizer()
    model = MagicMock()
    # The (None, None) call resolves the model and tokenizer through these getters;
    # point them at the same fakes so no real model loads and skip mode is irrelevant.
    with (
        patch.object(model_load, pipeline_factory) as factory,
        patch.object(model_load, model_getter, return_value=model),
        patch.object(model_load, tokenizer_getter, return_value=tokenizer),
    ):
        first = getattr(model_load, classifier_getter)(model, tokenizer)
        # The guardrail client and the ML eval scorers both go through this getter
        second = getattr(model_load, classifier_getter)(None, None)

    assert first is second
    factory.assert_called_once()
    assert tokenizer.truncation is True
    assert tokenizer.calls == [{"truncation": True, "max_length": 512}]


def _score_during_a_chunker_call(score, gate: HoldFirstChunkerCall) -> list[Exception]:
    """Run a second score() while the first is held inside its chunker tokenizer call."""
    errors: list[Exception] = []

    def record() -> None:
        try:
            score()
        except Exception as e:
            errors.append(e)

    first = threading.Thread(target=record)
    first.start()
    assert gate.held.wait(timeout=5), "the first chunker call never started"
    record()
    gate.release.set()
    first.join(timeout=5)
    return errors


@pytest.mark.unit_tests
def test_prompt_injection_chunker_and_pipeline_run_concurrently_without_errors():
    gate = HoldFirstChunkerCall()
    pipeline_tokenizer = FakeFastTokenizer(truncation=True, gate=gate)
    chunking_tokenizer = FakeFastTokenizer(truncation=False, gate=gate)

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
        errors = _score_during_a_chunker_call(lambda: classifier.score(request), gate)

    assert errors == []
    assert pipeline_tokenizer.truncation is True
    assert chunking_tokenizer.truncation is False


@pytest.mark.unit_tests
def test_toxicity_chunker_and_pipeline_run_concurrently_without_errors():
    gate = HoldFirstChunkerCall()
    pipeline_tokenizer = FakeFastTokenizer(truncation=True, gate=gate)
    chunking_tokenizer = FakeFastTokenizer(truncation=False, gate=gate)

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
        errors = _score_during_a_chunker_call(
            lambda: results.append(scorer.score(request).result),
            gate,
        )

    assert errors == []
    assert set(results) == {RuleResultEnum.PASS}
