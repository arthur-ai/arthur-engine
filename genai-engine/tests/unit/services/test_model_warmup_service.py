"""Unit tests for the background model warmup service."""

from __future__ import annotations

import time
from typing import Generator
from unittest.mock import patch

import pytest

from services.model_warmup_service import (
    DEFAULT_RETRY_AFTER_SECONDS,
    ModelKey,
    ModelLoadStatus,
    ModelWarmupService,
    _ModelLoaderSpec,
    fail_fast_when_warming,
)


def _spec(
    key: ModelKey,
    loader,
    enabled: bool = True,
    rule_types: tuple[str, ...] = (),
) -> _ModelLoaderSpec:
    return _ModelLoaderSpec(
        key=key,
        loader=loader,
        rule_types=rule_types,
        enabled=lambda: enabled,
    )


@pytest.fixture
def isolated_service() -> Generator[ModelWarmupService, None, None]:
    """A fresh service instance per test, never the package singleton."""
    service = ModelWarmupService()
    yield service
    service.shutdown()


def _wait_until(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


@pytest.mark.unit_tests
def test_status_starts_pending_for_unknown_key() -> None:
    service = ModelWarmupService()
    # No specs configured at all.
    assert service.is_ready(ModelKey.TOXICITY) is False
    assert service.get_status(ModelKey.TOXICITY) == ModelLoadStatus.PENDING


@pytest.mark.unit_tests
def test_skip_model_loading_marks_all_skipped(
    isolated_service: ModelWarmupService,
) -> None:
    isolated_service.configure(
        [_spec(ModelKey.PROMPT_INJECTION, lambda: None)],
    )
    with patch(
        "services.model_warmup_service.skip_model_loading",
        return_value=True,
    ):
        isolated_service.start_warmup()
    assert (
        isolated_service.get_status(ModelKey.PROMPT_INJECTION)
        == ModelLoadStatus.SKIPPED
    )
    assert isolated_service.is_ready(ModelKey.PROMPT_INJECTION) is True


@pytest.mark.unit_tests
def test_warmup_marks_model_ready(
    isolated_service: ModelWarmupService,
) -> None:
    calls: list[ModelKey] = []

    def loader() -> None:
        calls.append(ModelKey.TOXICITY)

    isolated_service.configure([_spec(ModelKey.TOXICITY, loader)])
    with patch(
        "services.model_warmup_service.skip_model_loading",
        return_value=False,
    ):
        isolated_service.start_warmup()
    assert _wait_until(lambda: isolated_service.is_ready(ModelKey.TOXICITY))
    assert calls == [ModelKey.TOXICITY]
    assert isolated_service.get_status(ModelKey.TOXICITY) == ModelLoadStatus.READY


@pytest.mark.unit_tests
def test_disabled_spec_is_skipped_without_calling_loader(
    isolated_service: ModelWarmupService,
) -> None:
    called = []

    def loader() -> None:
        called.append(True)

    isolated_service.configure(
        [_spec(ModelKey.RELEVANCE_BERT, loader, enabled=False)],
    )
    with patch(
        "services.model_warmup_service.skip_model_loading",
        return_value=False,
    ):
        isolated_service.start_warmup()
    assert _wait_until(
        lambda: isolated_service.get_status(ModelKey.RELEVANCE_BERT)
        == ModelLoadStatus.SKIPPED,
    )
    assert called == []
    assert isolated_service.is_ready(ModelKey.RELEVANCE_BERT) is True


@pytest.mark.unit_tests
def test_failed_loader_eventually_succeeds_via_retry(
    isolated_service: ModelWarmupService,
) -> None:
    attempts = {"count": 0}

    def flaky_loader() -> None:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("nope")

    isolated_service.configure([_spec(ModelKey.PROFANITY, flaky_loader)])
    # Drive backoff to ~0 so the test doesn't sleep 30s.
    with (
        patch(
            "services.model_warmup_service._MIN_RETRY_BACKOFF_SECONDS",
            0.0,
        ),
        patch(
            "services.model_warmup_service.skip_model_loading",
            return_value=False,
        ),
    ):
        isolated_service.start_warmup()
        assert _wait_until(
            lambda: isolated_service.is_ready(ModelKey.PROFANITY),
        )
    assert attempts["count"] == 2


@pytest.mark.unit_tests
def test_retry_after_seconds_scales_with_pending_work(
    isolated_service: ModelWarmupService,
) -> None:
    isolated_service.configure(
        [
            _spec(ModelKey.PROMPT_INJECTION, lambda: None),
            _spec(ModelKey.TOXICITY, lambda: None),
        ],
    )
    # Nothing has run yet; both are PENDING.
    assert isolated_service.retry_after_seconds() >= DEFAULT_RETRY_AFTER_SECONDS * 2


@pytest.mark.unit_tests
def test_overall_status_reflects_partial_failure(
    isolated_service: ModelWarmupService,
) -> None:
    def good() -> None:
        return None

    def bad() -> None:
        raise RuntimeError("boom")

    isolated_service.configure(
        [
            _spec(ModelKey.PROMPT_INJECTION, good),
            _spec(ModelKey.TOXICITY, bad),
        ],
    )
    with (
        patch(
            "services.model_warmup_service._MIN_RETRY_BACKOFF_SECONDS",
            9999.0,
        ),
        patch(
            "services.model_warmup_service.skip_model_loading",
            return_value=False,
        ),
    ):
        isolated_service.start_warmup()
        assert _wait_until(
            lambda: isolated_service.get_status(ModelKey.TOXICITY)
            == ModelLoadStatus.FAILED
            and isolated_service.get_status(ModelKey.PROMPT_INJECTION)
            == ModelLoadStatus.READY,
        )

    snapshot = isolated_service.get_overall_status()
    assert snapshot.overall_status.value == "partial"
    keys = {entry.key for entry in snapshot.models}
    assert keys == {"prompt_injection", "toxicity"}


@pytest.mark.unit_tests
def test_warn_throttled_emits_at_most_once_per_window(
    isolated_service: ModelWarmupService,
) -> None:
    with patch("services.model_warmup_service.logger.warning") as mock_warn:
        isolated_service.warn_throttled(ModelKey.TOXICITY, "hello")
        isolated_service.warn_throttled(ModelKey.TOXICITY, "hello")
        isolated_service.warn_throttled(ModelKey.TOXICITY, "hello")
    assert mock_warn.call_count == 1


@pytest.mark.unit_tests
def test_fail_fast_when_warming_env_default_false() -> None:
    with patch(
        "services.model_warmup_service.get_env_var",
        return_value="false",
    ):
        assert fail_fast_when_warming() is False


@pytest.mark.unit_tests
def test_fail_fast_when_warming_env_true() -> None:
    with patch(
        "services.model_warmup_service.get_env_var",
        return_value="TRUE",
    ):
        assert fail_fast_when_warming() is True
