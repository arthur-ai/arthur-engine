"""How a SIEM source's tls_verification decides what the engine trusts.

Against a real HTTPS server on 127.0.0.1, with certificates made for the test. A CA put
in REQUESTS_CA_BUNDLE stands for a publicly trusted one: requests loads that bundle into
the connection exactly where it would load certifi, so a mode that leaks one leaks the
other.
"""

import datetime as dt
import http.server
import ipaddress
import ssl
import threading
from pathlib import Path
from typing import Iterator, NamedTuple

import pytest
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from discovery.siem.tls import TLSVerification, tls_session
from job_executors.discovery_scan import DiscoveryConfigurationError


class _CA(NamedTuple):
    key: ec.EllipticCurvePrivateKey
    cert: x509.Certificate

    @property
    def pem(self) -> str:
        return self.cert.public_bytes(serialization.Encoding.PEM).decode()


def _ca(name: str) -> _CA:
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False
        )
        .sign(key, hashes.SHA256())
    )
    return _CA(key, cert)


def _server_pem(ca: _CA, tmp: Path) -> tuple[Path, Path]:
    """A certificate for 127.0.0.1 and localhost, issued by `ca`."""
    key = ec.generate_private_key(ec.SECP256R1())
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(ca.cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca.key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(ca.key, hashes.SHA256())
    )
    cert_path, key_path = tmp / "server.pem", tmp / "server.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


class _OK(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def server_ca() -> _CA:
    """The CA that issued the server's certificate."""
    return _ca("server ca")


@pytest.fixture(scope="module")
def other_ca() -> _CA:
    """A CA that issued nothing the server presents."""
    return _ca("other ca")


@pytest.fixture(scope="module")
def https_url(
    server_ca: _CA, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[str]:
    cert_path, key_path = _server_pem(server_ca, tmp_path_factory.mktemp("tls"))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    httpd = http.server.HTTPServer(("127.0.0.1", 0), _OK)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"https://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()


def _bundle(ca: _CA, tmp_path: Path) -> str:
    path = tmp_path / "bundle.pem"
    path.write_text(ca.pem)
    return str(path)


def test_ca_only_trusts_the_sources_ca(server_ca: _CA, https_url: str) -> None:
    session = tls_session(server_ca.pem, TLSVerification.CA_ONLY, "Test")
    assert session.get(https_url, timeout=5).status_code == 200


def test_ca_only_trusts_nothing_but_the_sources_ca(
    server_ca: _CA,
    other_ca: _CA,
    https_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The server's CA is "publicly trusted" here, as certifi's would be. ca_only with
    # another CA must still refuse it: without a hostname check, any public CA's
    # certificate for any host would otherwise pass.
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", _bundle(server_ca, tmp_path))
    session = tls_session(other_ca.pem, TLSVerification.CA_ONLY, "Test")
    with pytest.raises(requests.exceptions.SSLError):
        session.get(https_url, timeout=5)


def test_ca_only_without_a_ca_certificate_is_a_configuration_error() -> None:
    with pytest.raises(DiscoveryConfigurationError, match="no ca_certificate"):
        tls_session(None, TLSVerification.CA_ONLY, "Test")


@pytest.mark.parametrize("variable", ["REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"])
def test_off_stays_off_when_the_engine_sets_a_ca_bundle(
    variable: str,
    other_ca: _CA,
    https_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Engines behind a TLS-inspecting egress proxy set these. requests would replace
    # verify=False with the bundle's path and require a certificate it signed.
    monkeypatch.setenv(variable, _bundle(other_ca, tmp_path))
    session = tls_session(None, TLSVerification.OFF, "Test")
    assert session.get(https_url, timeout=5).status_code == 200


def test_off_ignores_a_ca_certificate(https_url: str) -> None:
    session = tls_session("not a certificate", TLSVerification.OFF, "Test")
    assert session.get(https_url, timeout=5).status_code == 200


def test_full_trusts_the_sources_ca_and_checks_the_host(
    server_ca: _CA, other_ca: _CA, https_url: str
) -> None:
    assert (
        tls_session(server_ca.pem, TLSVerification.FULL, "Test")
        .get(https_url, timeout=5)
        .status_code
        == 200
    )
    with pytest.raises(requests.exceptions.SSLError):
        tls_session(other_ca.pem, TLSVerification.FULL, "Test").get(
            https_url, timeout=5
        )
