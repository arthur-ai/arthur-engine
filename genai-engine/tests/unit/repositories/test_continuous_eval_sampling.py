import uuid

import pytest

from repositories.continuous_evals_repository import is_trace_sampled

# Fixed ids: unit tests must be deterministic.
_NAMESPACE = uuid.UUID("6f1c1c0e-5351-4a3e-9b7d-000000005351")


def _trace_ids(n: int) -> list[str]:
    return [uuid.uuid5(_NAMESPACE, str(i)).hex for i in range(n)]


@pytest.mark.unit_tests
@pytest.mark.parametrize("sample_rate", [None, 1.0])
def test_unset_or_full_rate_samples_every_trace(sample_rate):
    assert all(is_trace_sampled(t, sample_rate) for t in _trace_ids(1000))


@pytest.mark.unit_tests
def test_sampling_is_deterministic_per_trace():
    trace_ids = _trace_ids(500)
    first = [is_trace_sampled(t, 0.3) for t in trace_ids]
    second = [is_trace_sampled(t, 0.3) for t in trace_ids]
    assert first == second


@pytest.mark.unit_tests
def test_sampling_is_stable_across_processes():
    # sha256, not hash(): Python's str hash is salted per process.
    assert is_trace_sampled("0af7651916cd43dd8448eb211c80319c", 0.1) is True
    assert is_trace_sampled("4bf92f3577b34da6a3ce929d0e0e4736", 0.1) is False


@pytest.mark.unit_tests
@pytest.mark.parametrize("sample_rate", [0.01, 0.1, 0.25, 0.5, 0.9])
def test_sampling_matches_rate_over_many_traces(sample_rate):
    n = 20000
    sampled = sum(is_trace_sampled(t, sample_rate) for t in _trace_ids(n))
    # Binomial sd at n=20000 is under 0.0036.
    assert abs(sampled / n - sample_rate) < 0.015


@pytest.mark.unit_tests
def test_lower_rate_samples_a_subset_of_higher_rate():
    trace_ids = _trace_ids(2000)
    low = {t for t in trace_ids if is_trace_sampled(t, 0.1)}
    high = {t for t in trace_ids if is_trace_sampled(t, 0.5)}
    assert low <= high
