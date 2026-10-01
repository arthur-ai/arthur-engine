"""How a SIEM connector trusts the server it sends a credential to.

Every SIEM source carries the same two optional fields, `ca_certificate` and
`tls_verification`, because the same three situations come up whichever SIEM it is:

* `full` (the default): issuer and hostname, against the engine's system CAs plus the
  source's `ca_certificate` when it has one.
* `ca_only`: issuer only. For a certificate that names no host the engine can reach it
  by -- Splunk's default `SplunkServerDefaultCert`, or Elasticsearch's auto-generated one
  reached through an alias it was not issued for. Trusting the CA without matching the
  hostname is still a real check.
* `off`: no check at all, for the rest.

`requests` cannot express `ca_only` -- `verify` is all or nothing -- so the context is
carried into urllib3 by an adapter instead.
"""

import ssl
from enum import Enum
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter


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
        raise ValueError(
            f"{source_label} source's tls_verification is {value!r}; expected one of "
            f"{', '.join(m.value for m in TLSVerification)}.",
        ) from None


class _TLSAdapter(HTTPAdapter):
    """Carries an SSL context, and whether to match the hostname, into urllib3."""

    def __init__(self, ssl_context: ssl.SSLContext, match_hostname: bool) -> None:
        self._ssl_context = ssl_context
        self._match_hostname = match_hostname
        super().__init__()

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
    context = ssl.create_default_context()
    if ca_certificate:
        try:
            context.load_verify_locations(cadata=ca_certificate)
        except ssl.SSLError as exc:
            raise ValueError(
                f"{source_label} source's ca_certificate is not a PEM certificate: "
                f"{exc}",
            ) from exc
    if mode is not TLSVerification.FULL:
        context.check_hostname = False
    if mode is TLSVerification.OFF:
        context.verify_mode = ssl.CERT_NONE

    session = requests.Session()
    session.verify = mode is not TLSVerification.OFF
    session.mount(
        "https://",
        _TLSAdapter(context, match_hostname=mode is TLSVerification.FULL),
    )
    return session
