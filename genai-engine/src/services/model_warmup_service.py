"""Background warmup of ML models so the API doesn't block on startup.

The :class:`ModelWarmupService` is a per-process singleton that:

- Walks a configured list of model loaders in priority order on a single
  daemon thread that is started from FastAPI's ``lifespan``.
- Exposes an ``is_ready(key)`` lock-free read that lets request handlers
  cheaply decide whether to run a check or return ``MODEL_NOT_AVAILABLE``.
- Applies exponential backoff to retry failed loads so transient network
  blips don't permanently disable a check.

Status reads are intentionally on the hot request path: they must be
cheap and never block. State mutation is serialized through ``_state_lock``.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from clients.telemetry.telemetry_client import (
    TelemetryEventTypes,
    send_telemetry_event,
)
from schemas.enums import ModelLoadStatus, OverallWarmupStatus
from schemas.response_schemas import ModelStatusEntry, ModelStatusResponse
from utils import constants
from utils.utils import (
    get_env_var,
    relevance_models_enabled,
    skip_model_loading,
)

logger = logging.getLogger(__name__)


class ModelKey(str, Enum):
    """Identifiers for each model the engine warms in the background."""

    PROMPT_INJECTION = "prompt_injection"
    TOXICITY = "toxicity"
    PROFANITY = "profanity"
    HARMFUL_REQUEST = "harmful_request"
    CLAIM_CLASSIFIER = "claim_classifier"
    PII_PRESIDIO = "pii_presidio"
    PII_GLINER = "pii_gliner"
    RELEVANCE_BERT = "relevance_bert"
    RELEVANCE_RERANKER = "relevance_reranker"


# Number of seconds the engine asks clients to wait before retrying when a
# required model isn't ready yet. Configurable via env var; defaults to 30s.
DEFAULT_RETRY_AFTER_SECONDS = 30

# Backoff bounds for retrying failed loads.
_MIN_RETRY_BACKOFF_SECONDS = 30
_MAX_RETRY_BACKOFF_SECONDS = 5 * 60


@dataclass
class ModelStateRecord:
    """Mutable state per model. Reads of ``status`` are racy but safe.

    Python's GIL makes attribute reads atomic for our purposes; the
    ``status`` field is the single value any hot path actually inspects.
    """

    key: ModelKey
    status: ModelLoadStatus = ModelLoadStatus.PENDING
    last_error: Optional[str] = None
    last_error_type: Optional[str] = None
    last_attempt_ts: float = 0.0
    retry_count: int = 0
    rule_types: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class _ModelLoaderSpec:
    """Static description of how to warm a single model."""

    key: ModelKey
    loader: Callable[[], object]
    rule_types: tuple[str, ...]
    enabled: Callable[[], bool]


class ModelWarmupService:
    """Warms ML models in a single background thread."""

    def __init__(self) -> None:
        self._state_lock = threading.Lock()
        self._states: dict[ModelKey, ModelStateRecord] = {}
        self._specs: list[_ModelLoaderSpec] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._fully_warm_event = threading.Event()
        # Per-key throttle for "model not ready" warning logs so a busy
        # client can't flood the logs while waiting for warmup.
        self._last_warn_ts: dict[ModelKey, float] = {}
        self._warn_throttle_seconds = 60.0

    def configure(self, specs: list[_ModelLoaderSpec]) -> None:
        """Register loader specs; idempotent."""
        with self._state_lock:
            self._specs = list(specs)
            for spec in specs:
                if spec.key not in self._states:
                    self._states[spec.key] = ModelStateRecord(
                        key=spec.key,
                        rule_types=spec.rule_types,
                    )
                else:
                    self._states[spec.key].rule_types = spec.rule_types

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start_warmup(self) -> None:
        """Kick off the single background warmup thread; idempotent."""
        if skip_model_loading():
            logger.info(
                "Skipping model warmup - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
            )
            with self._state_lock:
                for state in self._states.values():
                    state.status = ModelLoadStatus.SKIPPED
            self._fully_warm_event.set()
            return

        with self._state_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._run,
                name="genai-engine-model-warmup",
                daemon=True,
            )
            self._thread.start()

    def ensure_warmup_started(self) -> None:
        """Idempotent fallback for request paths that hit a not-ready model.

        The normal flow starts warmup from ``server.lifespan``; this method
        exists so that an unusual startup ordering (e.g. a unit test using
        the app without ``lifespan``) cannot leave warmup permanently off.
        """
        if self._thread is None or not self._thread.is_alive():
            self.start_warmup()

    def shutdown(self) -> None:
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Status reads (hot path - must be cheap)
    # ------------------------------------------------------------------
    def is_ready(self, key: ModelKey) -> bool:
        state = self._states.get(key)
        if state is None:
            return False
        return state.status in (ModelLoadStatus.READY, ModelLoadStatus.SKIPPED)

    def get_status(self, key: ModelKey) -> ModelLoadStatus:
        state = self._states.get(key)
        if state is None:
            return ModelLoadStatus.PENDING
        return state.status

    def is_fully_warm(self) -> bool:
        return self._fully_warm_event.is_set()

    def retry_after_seconds(self) -> int:
        """Suggested ``Retry-After`` value for clients that hit unready models.

        Scales with the number of models still pending so callers wait
        proportionally longer at the start of warmup.
        """
        base = _retry_after_floor_seconds()
        pending = 0
        for state in self._states.values():
            if state.status not in (
                ModelLoadStatus.READY,
                ModelLoadStatus.SKIPPED,
                ModelLoadStatus.FAILED,
            ):
                pending += 1
        return max(base, base * max(pending, 1))

    def get_overall_status(self) -> ModelStatusResponse:
        """Snapshot of every model's status; safe to call from request paths.

        ``last_error`` on each entry is redacted to the exception class name
        so the public ``/system/model_status`` and ``/readyz`` endpoints can't
        leak raw exception strings (which could include model-repo URLs or
        local paths). Full error messages stay in the in-memory state for
        server-side logging.
        """
        models: list[ModelStatusEntry] = []
        any_failed = False
        any_unready = False
        any_ready = False
        any_real_state = False
        for state in self._states.values():
            models.append(
                ModelStatusEntry(
                    key=state.key.value,
                    status=state.status,
                    rule_types=list(state.rule_types),
                    last_error=state.last_error_type,
                    retry_count=state.retry_count,
                ),
            )
            if state.status == ModelLoadStatus.FAILED:
                any_failed = True
            if state.status in (ModelLoadStatus.READY, ModelLoadStatus.SKIPPED):
                any_ready = True
            if state.status not in (
                ModelLoadStatus.READY,
                ModelLoadStatus.SKIPPED,
                ModelLoadStatus.FAILED,
            ):
                any_unready = True
            if state.status != ModelLoadStatus.SKIPPED:
                any_real_state = True

        if not any_real_state:
            overall = OverallWarmupStatus.SKIPPED
        elif any_unready:
            overall = OverallWarmupStatus.WARMING
        elif any_failed and any_ready:
            overall = OverallWarmupStatus.PARTIAL
        elif any_failed:
            overall = OverallWarmupStatus.FAILED
        else:
            overall = OverallWarmupStatus.READY

        return ModelStatusResponse(
            overall_status=overall,
            retry_after_seconds=self.retry_after_seconds(),
            models=models,
        )

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def warn_throttled(self, key: ModelKey, message: str) -> None:
        """Log ``message`` at WARN at most once per minute per ``key``."""
        now = time.monotonic()
        last = self._last_warn_ts.get(key, 0.0)
        if now - last >= self._warn_throttle_seconds:
            self._last_warn_ts[key] = now
            logger.warning(message)

    # ------------------------------------------------------------------
    # Background worker
    # ------------------------------------------------------------------
    def _run(self) -> None:
        logger.info("Model warmup thread started")
        # Snapshot the spec list under the lock; mutation after start is rare.
        with self._state_lock:
            specs = list(self._specs)

        for spec in specs:
            if self._stop_event.is_set():
                return
            if not spec.enabled():
                self._set_status(spec.key, ModelLoadStatus.SKIPPED)
                continue
            self._warm_one(spec)

        # Recheck for failures and retry with backoff until everything is
        # READY/SKIPPED or the process shuts down. This loop is cheap: if
        # everything succeeded the first time, it exits immediately.
        while not self._stop_event.is_set():
            failed = [
                spec
                for spec in specs
                if self._states[spec.key].status == ModelLoadStatus.FAILED
            ]
            if not failed:
                break
            for spec in failed:
                if self._stop_event.is_set():
                    return
                state = self._states[spec.key]
                backoff = min(
                    _MIN_RETRY_BACKOFF_SECONDS * (2**state.retry_count),
                    _MAX_RETRY_BACKOFF_SECONDS,
                )
                wait_left = backoff - (time.monotonic() - state.last_attempt_ts)
                if wait_left > 0:
                    self._stop_event.wait(min(wait_left, 5.0))
                    continue
                self._warm_one(spec)

        if self._all_terminal():
            self._fully_warm_event.set()
            try:
                send_telemetry_event(TelemetryEventTypes.MODELS_WARM_COMPLETED)
            except Exception:
                logger.debug("Telemetry MODELS_WARM_COMPLETED failed", exc_info=True)
        logger.info("Model warmup thread exiting")

    def _all_terminal(self) -> bool:
        return all(
            state.status in (ModelLoadStatus.READY, ModelLoadStatus.SKIPPED)
            for state in self._states.values()
        )

    def _warm_one(self, spec: _ModelLoaderSpec) -> None:
        self._set_status(spec.key, ModelLoadStatus.LOADING)
        with self._state_lock:
            self._states[spec.key].last_attempt_ts = time.monotonic()
        try:
            spec.loader()
            self._set_status(spec.key, ModelLoadStatus.READY)
            logger.info("Model warmed: %s", spec.key.value)
        except Exception as exc:
            logger.exception("Model warmup failed for %s", spec.key.value)
            with self._state_lock:
                state = self._states[spec.key]
                state.status = ModelLoadStatus.FAILED
                state.last_error = str(exc)
                state.last_error_type = type(exc).__name__
                state.retry_count += 1

    def _set_status(self, key: ModelKey, status: ModelLoadStatus) -> None:
        with self._state_lock:
            self._states[key].status = status


def _retry_after_floor_seconds() -> int:
    raw = get_env_var(
        constants.GENAI_ENGINE_MODEL_WARMUP_RETRY_AFTER_SECONDS_ENV_VAR,
        none_on_missing=True,
    )
    if raw is None:
        return DEFAULT_RETRY_AFTER_SECONDS
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "Invalid %s=%r; falling back to default %d",
            constants.GENAI_ENGINE_MODEL_WARMUP_RETRY_AFTER_SECONDS_ENV_VAR,
            raw,
            DEFAULT_RETRY_AFTER_SECONDS,
        )
        return DEFAULT_RETRY_AFTER_SECONDS
    return max(value, 1)


def fail_fast_when_warming() -> bool:
    """Whether to return 503 instead of 200+Retry-After while warming."""
    raw = get_env_var(
        constants.GENAI_ENGINE_FAIL_FAST_WHEN_WARMING_ENV_VAR,
        none_on_missing=False,
        default="false",
    )
    return raw is not None and raw.lower() == "true"


# ----------------------------------------------------------------------
# Singleton wiring
# ----------------------------------------------------------------------
_SINGLETON: Optional[ModelWarmupService] = None
_SINGLETON_LOCK = threading.Lock()


def _build_default_specs() -> list[_ModelLoaderSpec]:
    """Build the default warmup specs.

    Loaders are tiny named closures so failures show up in tracebacks with
    a meaningful function name rather than ``<lambda>``. They're imported
    lazily so importing this module never imports heavy ML dependencies
    (transformers, torch, etc.) just to read state.
    """
    from utils import model_load
    from utils.model_load import USE_PII_MODEL_V2

    def _always_enabled() -> bool:
        return True

    def _relevance_enabled() -> bool:
        return relevance_models_enabled()

    def _pii_v2_enabled() -> bool:
        return USE_PII_MODEL_V2

    def _load_prompt_injection() -> None:
        model_load.get_prompt_injection_model()
        model_load.get_prompt_injection_tokenizer()
        model_load.get_prompt_injection_classifier(None, None)

    def _load_toxicity() -> None:
        model_load.get_toxicity_model()
        model_load.get_toxicity_tokenizer()
        model_load.get_toxicity_classifier(None, None)

    def _load_profanity() -> None:
        model_load.get_profanity_classifier()

    def _load_harmful_request() -> None:
        # In Arthur Engine the harmful-request classifier is intentionally a
        # no-op (the loader returns None unless given a concrete model+
        # tokenizer pair, which the engine never provides). We still keep a
        # warmup entry so /system/model_status reports it consistently.
        model_load.get_harmful_request_classifier(None, None)

    def _load_claim_classifier() -> None:
        model_load.get_claim_classifier_embedding_model()

    def _load_pii_presidio() -> None:
        model_load.get_presidio_analyzer()

    def _load_pii_gliner() -> None:
        model_load.get_gliner_tokenizer()
        model_load.get_gliner_model()

    def _load_relevance_bert() -> None:
        model_load.get_bert_scorer()

    def _load_relevance_reranker() -> None:
        model_load.get_relevance_reranker()

    # Order matters: cheap, frequently-used checks first so they're ready
    # for incoming traffic before the larger relevance/PII models load.
    return [
        _ModelLoaderSpec(
            key=ModelKey.PROMPT_INJECTION,
            loader=_load_prompt_injection,
            rule_types=("PromptInjectionRule",),
            enabled=_always_enabled,
        ),
        _ModelLoaderSpec(
            key=ModelKey.TOXICITY,
            loader=_load_toxicity,
            rule_types=("ToxicityRule",),
            enabled=_always_enabled,
        ),
        _ModelLoaderSpec(
            key=ModelKey.PROFANITY,
            loader=_load_profanity,
            rule_types=("ToxicityRule",),
            enabled=_always_enabled,
        ),
        _ModelLoaderSpec(
            key=ModelKey.HARMFUL_REQUEST,
            loader=_load_harmful_request,
            rule_types=("ToxicityRule",),
            enabled=_always_enabled,
        ),
        _ModelLoaderSpec(
            key=ModelKey.CLAIM_CLASSIFIER,
            loader=_load_claim_classifier,
            rule_types=("ModelHallucinationRuleV2",),
            enabled=_always_enabled,
        ),
        _ModelLoaderSpec(
            key=ModelKey.PII_PRESIDIO,
            loader=_load_pii_presidio,
            rule_types=("PIIDataRule",),
            enabled=_always_enabled,
        ),
        _ModelLoaderSpec(
            key=ModelKey.PII_GLINER,
            loader=_load_pii_gliner,
            rule_types=("PIIDataRule",),
            enabled=_pii_v2_enabled,
        ),
        _ModelLoaderSpec(
            key=ModelKey.RELEVANCE_BERT,
            loader=_load_relevance_bert,
            rule_types=("QueryRelevance", "ResponseRelevance"),
            enabled=_relevance_enabled,
        ),
        _ModelLoaderSpec(
            key=ModelKey.RELEVANCE_RERANKER,
            loader=_load_relevance_reranker,
            rule_types=("QueryRelevance", "ResponseRelevance"),
            enabled=_relevance_enabled,
        ),
    ]


def get_model_warmup_service() -> ModelWarmupService:
    """Return the per-process warmup service singleton."""
    global _SINGLETON
    if _SINGLETON is not None:
        return _SINGLETON
    with _SINGLETON_LOCK:
        if _SINGLETON is None:
            service = ModelWarmupService()
            service.configure(_build_default_specs())
            _SINGLETON = service
    return _SINGLETON


def reset_model_warmup_service_for_testing() -> None:
    """Test-only hook to reset the singleton between tests."""
    global _SINGLETON
    with _SINGLETON_LOCK:
        if _SINGLETON is not None:
            _SINGLETON.shutdown()
        _SINGLETON = None
