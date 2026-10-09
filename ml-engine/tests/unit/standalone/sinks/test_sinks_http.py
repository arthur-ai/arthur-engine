"""The HTTP sink base, against a minimal target and a mocked HTTP layer.

The tests that matter most are the scrubbing ones: a delivery failure becomes a scan's
error, which is logged and sent on as an outcome event, and nothing upstream of the
sink knows the destination's secrets to take them back out.
"""

import datetime as dt
import json
import logging
import re
from pathlib import Path
from typing import Any, Iterator, Literal, Sequence

import pytest
import requests
import responses
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from discovery.siem.tls import TLSVerification
from standalone.config_values import BASE_DIR_CONTEXT
from standalone.sinks.common import Sink, SinkDeliveryError
from standalone.sinks.http import MAX_RETRY_DELAY_SECONDS, HttpDestination, HttpSink

LOG = logging.getLogger("sinks-http-test")
SECRET_PATH = "/ingest/T0KEN1234abcd"
URL = f"https://siem.example.com{SECRET_PATH}"
SECRET = "dest-s3cret-0004"


class Sleeps:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


class StubDestination(HttpDestination):
    type: Literal["stub"] = "stub"

    def build_sink(self, logger: logging.Logger) -> Sink:
        return StubSink(self, logger)


class StubSink(HttpSink):
    """Frames a batch as a JSON array and declares one secret."""

    kind = "stub"

    def _destination_secrets(self) -> tuple[str, ...]:
        return (SECRET,)

    def _encode(self, batch: Sequence[dict[str, Any]]) -> tuple[bytes, dict[str, str]]:
        return json.dumps(list(batch)).encode(), {"X-Key": SECRET}


def sink(sleeps: Sleeps | None = None, **overrides: Any) -> StubSink:
    destination = StubDestination.model_validate({"url": URL, **overrides})
    return StubSink(destination, LOG, sleep=sleeps or Sleeps())


@pytest.fixture
def mock() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock() as rsps:
        yield rsps


# --- Config ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "allow_http", "error"),
    [
        ("https://siem.example.com/in", False, None),
        ("http://siem.example.com/in", True, None),
        ("http://siem.example.com/in", False, "allow_insecure_http"),
        ("siem.example.com/in", False, "absolute URL"),
    ],
)
def test_the_url_must_be_https_unless_opted_out(
    url: str,
    allow_http: bool,
    error: str | None,
) -> None:
    fields = {"url": url, "allow_insecure_http": allow_http}

    if error is None:
        StubDestination.model_validate(fields)
    else:
        with pytest.raises(ValueError, match=error):
            StubDestination.model_validate(fields)


def test_an_unknown_setting_is_refused() -> None:
    with pytest.raises(ValueError, match="batchsize"):
        StubDestination.model_validate({"url": URL, "batchsize": 5})


# --- Delivery ----------------------------------------------------------------------


def test_events_are_sent_in_batches_of_the_configured_size(
    mock: responses.RequestsMock,
) -> None:
    mock.add(responses.POST, URL)

    sink(batch_size=2).send([{"n": n} for n in range(5)])

    assert [len(json.loads(call.request.body)) for call in mock.calls] == [2, 2, 1]


def test_tls_verification_and_timeout_come_from_the_destination(
    mock: responses.RequestsMock,
) -> None:
    mock.add(responses.POST, URL)

    sink(tls_verification="off", timeout_seconds=5).send([{"n": 1}])

    kwargs = mock.calls[0].request.req_kwargs
    assert kwargs["verify"] is False
    assert kwargs["timeout"] == 5


def test_tls_verification_defaults_to_full() -> None:
    destination = StubDestination.model_validate({"url": URL})

    assert destination.tls_verification is TLSVerification.FULL
    assert destination.ca_certificate is None


def test_a_bare_yaml_off_turns_verification_off() -> None:
    """YAML reads an unquoted `off` as false."""
    destination = StubDestination.model_validate(
        {"url": URL, "tls_verification": False},
    )

    assert destination.tls_verification is TLSVerification.OFF


def test_ca_only_needs_a_ca_certificate() -> None:
    with pytest.raises(ValueError, match="ca_certificate is not set"):
        StubDestination.model_validate({"url": URL, "tls_verification": "ca_only"})


def test_a_ca_certificate_that_is_not_pem_is_refused_at_load() -> None:
    with pytest.raises(ValueError, match="not a PEM certificate"):
        StubDestination.model_validate({"url": URL, "ca_certificate": "nope"})


def test_a_ca_certificate_is_read_from_a_file(tmp_path: Path) -> None:
    pem = _a_ca_pem()
    (tmp_path / "ca.pem").write_text(pem)

    destination = StubDestination.model_validate(
        {
            "url": URL,
            "tls_verification": "ca_only",
            "ca_certificate": {"file": "ca.pem"},
        },
        context={BASE_DIR_CONTEXT: tmp_path},
    )

    assert destination.ca_certificate == pem


def test_turning_verification_off_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        sink(tls_verification="off")

    assert "TLS verification is off for stub at siem.example.com" in caplog.text


def test_an_untrusted_certificate_is_not_retried(mock: responses.RequestsMock) -> None:
    mock.add(
        responses.POST,
        URL,
        body=requests.exceptions.SSLError(
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
            "self-signed certificate",
        ),
    )
    sleeps = Sleeps()

    with pytest.raises(SinkDeliveryError) as caught:
        sink(sleeps).send([{"n": 1}])

    assert len(mock.calls) == 1
    assert sleeps.calls == []
    assert "does not trust" in str(caught.value)
    assert "ca_certificate" in str(caught.value)


def test_another_tls_failure_is_retried(mock: responses.RequestsMock) -> None:
    mock.add(
        responses.POST,
        URL,
        body=requests.exceptions.SSLError("EOF occurred in violation of protocol"),
    )
    mock.add(responses.POST, URL)

    sink().send([{"n": 1}])

    assert len(mock.calls) == 2


def _a_ca_pem() -> str:
    """A throwaway self-signed CA certificate, made for the test."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test ca")])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now)
        .not_valid_after(now + dt.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def test_a_transient_failure_is_retried_with_backoff(
    mock: responses.RequestsMock,
) -> None:
    mock.add(responses.POST, URL, status=503)
    mock.add(responses.POST, URL, status=502)
    mock.add(responses.POST, URL, status=200)
    sleeps = Sleeps()

    sink(sleeps).send([{"n": 1}])

    assert len(mock.calls) == 3
    assert sleeps.calls == [1.0, 2.0]


@pytest.mark.parametrize(
    ("retry_after", "expected"),
    [("5", 5.0), ("3600", MAX_RETRY_DELAY_SECONDS), ("Wed, 21 Oct 2026", 1.0)],
)
def test_retry_after_is_honoured_up_to_a_cap(
    mock: responses.RequestsMock,
    retry_after: str,
    expected: float,
) -> None:
    mock.add(responses.POST, URL, status=429, headers={"Retry-After": retry_after})
    mock.add(responses.POST, URL, status=200)
    sleeps = Sleeps()

    sink(sleeps).send([{"n": 1}])

    assert sleeps.calls == [expected]


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_a_redirect_is_refused_not_followed(
    mock: responses.RequestsMock,
    status: int,
) -> None:
    """Following one would re-send the events and every header but Authorization --
    the stub's X-Key included -- to a host nobody configured."""
    elsewhere = "https://elsewhere.example.net/collect"
    mock.add(responses.POST, URL, status=status, headers={"Location": elsewhere})
    sleeps = Sleeps()

    with pytest.raises(SinkDeliveryError) as e:
        sink(sleeps).send([{"n": 1}])

    # Nothing went to the Location: a followed redirect would show up as a second call.
    assert [call.request.url for call in mock.calls] == [URL]
    assert sleeps.calls == []
    assert e.value.status_code == status
    assert f"HTTP {status} (a redirect, which is not followed" in str(e.value)


def test_only_a_2xx_counts_as_delivered(mock: responses.RequestsMock) -> None:
    # 304 is under 400, so `response.ok` would have called this delivered.
    mock.add(responses.POST, URL, status=304)

    with pytest.raises(SinkDeliveryError, match="HTTP 304"):
        sink().send([{"n": 1}])


def test_a_refusal_is_not_retried(mock: responses.RequestsMock) -> None:
    mock.add(responses.POST, URL, status=403, json={"text": "Invalid token"})
    sleeps = Sleeps()

    with pytest.raises(SinkDeliveryError) as e:
        sink(sleeps).send([{"n": 1}])

    assert len(mock.calls) == 1 and sleeps.calls == []
    assert e.value.status_code == 403
    assert "stub at siem.example.com refused 1 event(s) with HTTP 403" in str(e.value)
    assert "Invalid token" in str(e.value)


def test_a_retry_waits_without_holding_up_other_scans(
    mock: responses.RequestsMock,
) -> None:
    """One sink serves every scan: a backoff must not hold the lock other scans'
    requests wait on."""
    mock.add(responses.POST, URL, status=503)
    mock.add(responses.POST, URL, status=200)
    held_while_waiting: list[bool] = []
    stub = sink()
    stub._sleep = lambda seconds: held_while_waiting.append(
        stub._session_lock.locked(),
    )

    stub.send([{"n": 1}])

    assert held_while_waiting == [False]


def test_retries_give_up_after_three_attempts(mock: responses.RequestsMock) -> None:
    for _ in range(3):
        mock.add(responses.POST, URL, status=503)

    with pytest.raises(SinkDeliveryError, match="HTTP 503"):
        sink().send([{"n": 1}])

    assert len(mock.calls) == 3


def test_a_connection_failure_is_retried_then_reported(
    mock: responses.RequestsMock,
) -> None:
    error = requests.ConnectionError(f"Max retries exceeded with url: {SECRET_PATH}")
    for _ in range(3):
        mock.add(responses.POST, URL, body=error)

    with pytest.raises(SinkDeliveryError) as e:
        sink().send([{"n": 1}])

    assert len(mock.calls) == 3
    assert "Could not reach stub at siem.example.com" in str(e.value)
    assert "T0KEN1234abcd" not in str(e.value)
    assert e.value.__cause__ is None


def test_earlier_batches_stay_delivered_when_a_later_one_fails(
    mock: responses.RequestsMock,
) -> None:
    mock.add(responses.POST, URL, status=200)
    mock.add(responses.POST, URL, status=400)

    with pytest.raises(SinkDeliveryError):
        sink(batch_size=1).send([{"n": 1}, {"n": 2}])

    assert len(mock.calls) == 2


# --- Scrubbing ---------------------------------------------------------------------


def test_a_refusal_never_echoes_a_secret_or_the_path(
    mock: responses.RequestsMock,
) -> None:
    mock.add(responses.POST, URL, status=401, body=f"denied {SECRET} on {SECRET_PATH}")

    with pytest.raises(SinkDeliveryError) as e:
        sink().send([{"n": 1}])

    assert SECRET not in str(e.value)
    assert "T0KEN1234abcd" not in str(e.value)


def test_the_host_is_named_without_userinfo() -> None:
    stub = sink(url="https://user:p4ssword@siem.example.com/in")

    with responses.RequestsMock() as mock:
        mock.add(
            responses.POST,
            re.compile(r"https://.*siem\.example\.com/in"),
            status=400,
            body="denied p4ssword",  # a destination that echoes what it was sent
        )
        with pytest.raises(SinkDeliveryError) as e:
            stub.send([{"n": 1}])

    assert "p4ssword" not in str(e.value)
    assert "stub at siem.example.com refused" in str(e.value)


def test_secrets_include_the_declared_ones_and_the_url_path() -> None:
    secrets = sink().secrets()

    assert SECRET in secrets and SECRET_PATH in secrets
