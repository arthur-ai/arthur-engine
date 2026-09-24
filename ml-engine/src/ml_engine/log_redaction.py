"""Credential redaction for everything a job writes to its log.

Scrubbing at each call site cannot hold: the job log exporter ships the traceback and
`str(exc)` of any record logged with `exc_info`, and the job executor logs every
failure that way on its way out, so a message redacted where it was written arrives at
the Platform raw one frame later. The redaction therefore lives here and is applied
where log records are shipped -- by `SecretRedactingFilter` on the job's logger, and
again by the exporter over each payload it builds.
"""

import logging
import re
import traceback
from typing import Iterable, Mapping, Optional, Sequence

_REDACTED = "[redacted]"

# The minimum length of a credential value worth removing by exact match. A value
# shorter than this is not a credential anyone issued, and scrubbing every occurrence
# of a two-character string would shred the message it was meant to protect.
_MIN_SECRET_LENGTH = 4

# What a credential looks like when nothing names it: a run of token characters that
# contains a digit, or is too long to be a word. Requiring one or the other is what
# lets "splunk enterprise" or "Basic configuration" through untouched.
_CREDENTIAL = (
    r"(?:(?=[A-Za-z0-9\-._~+/=]*\d)[A-Za-z0-9\-._~+/=]{8,}"
    r"|[A-Za-z0-9\-._~+/=]{24,})"
)

# The backstop, for credentials nobody handed us. The configured fields of a source are
# removed exactly -- but not what they are exchanged for at run time. An OAuth access
# token minted from a client_secret, or a Splunk session key minted from a password,
# exists only inside the scan, and is exactly what an SDK stringifies into an
# Authorization header when the call fails. These three rules cover that shape and
# nothing else: a generic `key: value` rule was tried and removed, because everything it
# caught was already covered exactly, while `token:`, `auth:` and `cookie:` in ordinary
# error prose made it eat the diagnosis.
#
# Each rule stops at whitespace, so the rest of the line -- the URL, the operation, the
# status code -- survives, and none of them matches its own placeholder, so text that
# has already been scrubbed comes through a second pass unchanged.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Any auth scheme, named or not: Bearer, Basic, Splunk, AWS4-HMAC-SHA256. The scheme
    # word is kept only when a credential-shaped value follows it, which is what keeps
    # an unrecognised scheme from being redacted in place of the credential behind it.
    re.compile(
        r"(?P<keep>\bauthorization\b[\"']?\s*[:=]\s*[\"']?"
        r"(?!(?:[A-Za-z][A-Za-z0-9-]*\s+)?\[redacted\])"
        rf"(?:[A-Za-z][A-Za-z0-9-]*\s+(?={_CREDENTIAL}))?)"
        r"[^,;}\]\s\"']+",
        re.IGNORECASE,
    ),
    # The same value logged without its header name.
    re.compile(
        rf"(?P<keep>\b(?:bearer|basic|splunk|token)\s+){_CREDENTIAL}",
        re.IGNORECASE,
    ),
    # Query parameters whose name *ends* in a credential word, matched as a whole
    # segment: access_token, X-Amz-Signature, api_key. A failing search still reports
    # the parameters that explain it (output_mode, count, earliest), and a name that
    # merely contains one -- design, keyword, author, signature_version -- is left alone.
    re.compile(
        r"(?P<keep>[?&](?:[A-Za-z0-9]+[_-])*"
        r"(?:token|key|apikey|sig|signature|secret|password|passwd|auth|credential)s?=)"
        r"(?!\[redacted\])[^&\s#]+",
        re.IGNORECASE,
    ),
)


def redact_secrets(text: str, known_secrets: Sequence[str] = ()) -> str:
    """Strip credentials out of text bound for the job log.

    Exact removal of the values in `known_secrets` is the control: those are the fields
    the Platform handed this job, so removing them needs no guess about how a vendor SDK
    formats its errors, and cannot take anything else with it. The patterns are a
    backstop for credentials derived at run time, which were never in that set -- see
    `_SECRET_PATTERNS`.
    """
    # Longest first: a short secret that happens to be a substring of a longer one must
    # not blank part of it and leave the remainder looking like ordinary text.
    for secret in sorted(set(known_secrets), key=len, reverse=True):
        if len(secret) >= _MIN_SECRET_LENGTH:
            text = text.replace(secret, _REDACTED)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda match: f"{match.group('keep')}{_REDACTED}", text)
    return text


def secret_values(credentials: Mapping[str, Optional[str]]) -> tuple[str, ...]:
    """The scrub set for one set of credentials: every value in it.

    The discovery credentials route returns sensitive fields *only*, so every value in
    it is a secret and no filtering is needed here. Keys are left out deliberately -- a
    field named "username" is not sensitive on its own, and removing the key names would
    redact the vocabulary an error uses to say which field was wrong.
    """
    return tuple(value for value in credentials.values() if value)


class SecretRedactingFilter(logging.Filter):
    """Scrubs every record a job's logger emits, before any handler sees it.

    Installed on the logger rather than on one handler, so the record is rewritten once
    and every destination -- the Platform exporter and the process's own stdout alike --
    gets the scrubbed text. The message is formatted and scrubbed in place, and the
    traceback is formatted into `exc_text`, which the standard formatter uses in
    preference to formatting `exc_info` itself.
    """

    def __init__(self) -> None:
        super().__init__()
        self._known_secrets: set[str] = set()

    def register(self, secrets: Iterable[str]) -> None:
        """Add values to remove by exact match, for the rest of this job."""
        self._known_secrets.update(secrets)

    def redact(self, text: str) -> str:
        return redact_secrets(text, tuple(self._known_secrets))

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.redact(record.getMessage())
        record.args = None
        if record.exc_info:
            record.exc_text = self.redact(
                "".join(traceback.format_exception(*record.exc_info)).rstrip("\n"),
            )
        return True


def register_secrets(logger: logging.Logger, secrets: Iterable[str]) -> None:
    """Have every redacting filter on `logger` remove these values from now on.

    A job reads its credentials long after its logger was set up, so this is how it
    tells the logger what to scrub. A logger with no filter installed -- one outside a
    job -- is left as it is.
    """
    secrets = tuple(secrets)
    for log_filter in logger.filters:
        if isinstance(log_filter, SecretRedactingFilter):
            log_filter.register(secrets)
