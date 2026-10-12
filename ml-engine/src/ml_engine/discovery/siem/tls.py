"""How a SIEM connector trusts the server it sends a credential to.

Every SIEM source carries the same two optional fields, `ca_certificate` and
`tls_verification`, because the same three situations come up whichever SIEM it is:

* `full` (the default): issuer and hostname, against the engine's system CAs plus the
  source's `ca_certificate` when it has one.
* `ca_only`: issuer only, against the source's `ca_certificate` and nothing else. For a
  certificate that names no host the engine can reach it by -- Splunk's default
  `SplunkServerDefaultCert`, or Elasticsearch's auto-generated one reached through an
  alias it was not issued for. Without the hostname check, trusting any public CA would
  accept any public site's certificate, so the source's CA is the only trust and is
  required.
* `off`: no check at all, for the rest.

`requests` cannot express either -- `verify` is all or nothing, and it loads certifi,
or a `REQUESTS_CA_BUNDLE` / `CURL_CA_BUNDLE` path, into the connection whenever it is
anything but False -- so the adapter carries the context into urllib3 and has the last
word on what the connection trusts.
"""

import re
import ssl
from enum import Enum
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter

from job_executors.discovery_scan import DiscoveryConfigurationError


class TLSVerification(str, Enum):
    """How a source's certificate is checked. See the module docstring."""

    FULL = "full"
    CA_ONLY = "ca_only"
    OFF = "off"


def parse_tls_verification(raw: Optional[str], source_label: str) -> TLSVerification:
    """The source's `tls_verification`, `full` when it is blank."""
    value = (raw or "").strip().lower()
    if not value:
        return TLSVerification.FULL
    try:
        return TLSVerification(value)
    except ValueError:
        raise DiscoveryConfigurationError(
            f"{source_label} source's tls_verification is {value!r}; expected one of "
            f"{', '.join(m.value for m in TLSVerification)}.",
        ) from None


# One PEM block, tolerant of where the line breaks went: a single-line form field strips
# every newline from a pasted certificate, which OpenSSL then reads as "no start line".
_PEM_BLOCK = re.compile(r"-----BEGIN ([A-Z0-9 ]+)-----(.*?)-----END \1-----", re.DOTALL)


def normalize_pem(text: str) -> str:
    """The certificate(s) in `text`, re-wrapped as OpenSSL expects.

    A PEM block's body is base64, in which whitespace carries nothing, so stripping it
    and wrapping at 64 columns gives back exactly the certificate that was pasted --
    however many line breaks it lost on the way. Text with no PEM block is returned as
    it came, so the load reports the real problem rather than this function guessing.
    """
    blocks = _PEM_BLOCK.findall(text)
    if not blocks:
        return text
    out = []
    for label, body in blocks:
        b64 = "".join(body.split())
        lines = [b64[i : i + 64] for i in range(0, len(b64), 64)]
        out.append(
            f"-----BEGIN {label}-----\n"
            + "\n".join(lines)
            + f"\n-----END {label}-----\n",
        )
    return "".join(out)


class _TLSAdapter(HTTPAdapter):
    """Carries an SSL context, and how the source's certificate is checked, into urllib3."""

    def __init__(self, ssl_context: ssl.SSLContext, mode: TLSVerification) -> None:
        self._ssl_context = ssl_context
        self._mode = mode
        self._match_hostname = mode is TLSVerification.FULL
        super().__init__()

    def cert_verify(self, conn: Any, url: str, verify: Any, cert: Any) -> None:
        # requests decides the connection's trust from `verify`, which an engine's
        # REQUESTS_CA_BUNDLE / CURL_CA_BUNDLE replaces per request, and loads certifi
        # or that bundle into it. The source's mode decides instead: `ca_only` trusts
        # its context's one CA alone, and `off` stays off. `trust_env` is left on so the
        # HTTPS_PROXY that `proxy_manager_for` serves still applies.
        super().cert_verify(conn, url, verify, cert)  # type: ignore[no-untyped-call]
        if self._mode is TLSVerification.FULL:
            return
        conn.ca_certs = None
        conn.ca_cert_dir = None
        conn.cert_reqs = (
            "CERT_NONE" if self._mode is TLSVerification.OFF else "CERT_REQUIRED"
        )

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        kwargs["ssl_context"] = self._ssl_context
        if not self._match_hostname:
            kwargs["assert_hostname"] = False
        super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, proxy: str, **proxy_kwargs: Any) -> Any:
        # An engine behind an HTTPS_PROXY reaches the server through a separate pool
        # manager that `init_poolmanager` never sees, so the trust is carried here too.
        proxy_kwargs["ssl_context"] = self._ssl_context
        if not self._match_hostname:
            proxy_kwargs["assert_hostname"] = False
        return super().proxy_manager_for(proxy, **proxy_kwargs)


def tls_session(
    ca_certificate: Optional[str],
    mode: TLSVerification,
    source_label: str,
) -> requests.Session:
    """A session that trusts the server the way the source says to."""
    if mode is TLSVerification.CA_ONLY and not ca_certificate:
        raise DiscoveryConfigurationError(
            f"{source_label} source's tls_verification is ca_only, which trusts the "
            f"source's ca_certificate and nothing else, but it has no ca_certificate.",
        )
    if mode is TLSVerification.FULL:
        context = ssl.create_default_context()
    else:
        # Empty: no system CAs. `ca_only` gets the source's CA below; `off` needs none.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
    # With verification off nothing reads the CA, so one that will not load must not
    # stop a scan an admin has deliberately set to trust anything.
    if ca_certificate and mode is not TLSVerification.OFF:
        try:
            context.load_verify_locations(cadata=normalize_pem(ca_certificate))
        except ssl.SSLError as exc:
            # Not chained: an ssl.SSLError is an OSError, and a classifier walking the
            # chain would read a certificate that never loaded as a network failure.
            # Nothing has been sent anywhere yet; this is the source's configuration.
            raise DiscoveryConfigurationError(
                f"{source_label} source's ca_certificate is not a PEM certificate: "
                f"{exc}",
            ) from None
    if mode is TLSVerification.OFF:
        context.verify_mode = ssl.CERT_NONE

    session = requests.Session()
    session.verify = mode is not TLSVerification.OFF
    session.mount("https://", _TLSAdapter(context, mode))
    return session
