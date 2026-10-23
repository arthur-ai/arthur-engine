"""Pulling a source and a destination out of one log line, as the source configures.

A REGEX WITH NAMED CAPTURE GROUPS, the idiom Splunk `rex`, Fluent Bit's regex parser and
Vector's `parse_regex` share: whatever a group is named is the field it extracts. `src`
and `dest` are required; `instance_id`, `interface_id`, `vpc_id`, `account_id` and
`timestamp` are read
when present; no other name is accepted, so a typo such as `dst` is refused rather than
silently extracting nothing. Both `(?P<name>...)` (Python) and `(?<name>...)` (PCRE,
Onigmo, Rust) spell a named group. The regex is searched, not anchored, as `rex` is.

A FORMAT INSTEAD OF A REGEX for the logs AWS writes in one fixed shape: `PRESETS` holds
the regex for each, so a preset and a hand-written pattern run the same code.

BOUNDED AT RUN TIME. Python's `re` cannot be interrupted, so a pattern with nested
quantifiers could hold a scan on one line for hours. Lines are matched with `regex`,
which takes a timeout, and lines longer than `MAX_LINE_LENGTH` are skipped unread; both
are counted and reported rather than failing the scan. The Platform refuses at save
time what does not compile, lacks a required group, or exceeds `MAX_PATTERN_LENGTH`;
`pattern_problem` is the same check here, for standalone engines.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import regex

REQUIRED_GROUPS = ("src", "dest")
OPTIONAL_GROUPS = ("instance_id", "interface_id", "vpc_id", "account_id", "timestamp")
MAX_PATTERN_LENGTH = 2048
MAX_LINE_LENGTH = 16_384
MATCH_TIMEOUT_SECONDS = 0.05

ROUTE53_RESOLVER_QUERY_LOG = "route53_resolver_query_log"
VPC_FLOW_LOG_V2 = "vpc_flow_log_v2"

# Route 53 Resolver query logs are one JSON object per line. Each field is found by its
# own lookahead, so the pattern holds whatever order the keys arrive in.
_ROUTE53_RESOLVER = (
    r'^(?=.*?"query_name"\s*:\s*"(?P<dest>[^"]+)")'
    r'(?=.*?"srcaddr"\s*:\s*"(?P<src>[^"]+)")'
    r'(?:(?=.*?"srcids"\s*:\s*\{[^}]*"instance"\s*:\s*"(?P<instance_id>[^"]+)"))?'
    r'(?:(?=.*?"vpc_id"\s*:\s*"(?P<vpc_id>[^"]+)"))?'
    r'(?:(?=.*?"account_id"\s*:\s*"(?P<account_id>[^"]+)"))?'
    r'(?:(?=.*?"query_timestamp"\s*:\s*"(?P<timestamp>[^"]+)"))?'
)

# The default VPC Flow Logs format, version 2: version account-id interface-id srcaddr
# dstaddr srcport dstport protocol packets bytes start end action log-status. NODATA and
# SKIPDATA lines carry `-` for the addresses and do not match.
_VPC_FLOW_LOG_V2 = (
    r"^2 (?P<account_id>\d{12}) (?P<interface_id>\S+) (?P<src>[0-9A-Fa-f.:]+) (?P<dest>[0-9A-Fa-f.:]+) "
    r"\d+ \d+ \d+ \d+ \d+ (?P<timestamp>\d+) \d+ (?:ACCEPT|REJECT) OK$"
)

PRESETS: dict[str, str] = {
    ROUTE53_RESOLVER_QUERY_LOG: _ROUTE53_RESOLVER,
    VPC_FLOW_LOG_V2: _VPC_FLOW_LOG_V2,
}

# `(?<name>` not preceded by an escaping backslash; `(?<=` and `(?<!` are lookbehinds.
_PCRE_NAMED_GROUP = re.compile(r"(?<!\\)((?:\\\\)*)\(\?<(?=[A-Za-z_])")


def normalized(pattern: str) -> str:
    """`pattern` with PCRE-style named groups rewritten to Python's spelling."""
    return _PCRE_NAMED_GROUP.sub(r"\1(?P<", pattern)


def pattern_problem(pattern: str) -> Optional[str]:
    """Why `pattern` cannot be an extraction regex, or None. Never echoes it."""
    if len(pattern) > MAX_PATTERN_LENGTH:
        return f"is longer than {MAX_PATTERN_LENGTH} characters"
    try:
        compiled = re.compile(normalized(pattern))
    except re.error as exc:
        return f"is not a valid regular expression ({exc.msg} at position {exc.pos})"
    names = set(compiled.groupindex)
    missing = [g for g in REQUIRED_GROUPS if g not in names]
    if missing:
        return "has no named group " + ", ".join(f"(?P<{g}>...)" for g in missing)
    unknown = sorted(names - set(REQUIRED_GROUPS) - set(OPTIONAL_GROUPS))
    if unknown:
        return (
            f"has named group(s) {', '.join(unknown)}; the names read are "
            f"{', '.join(REQUIRED_GROUPS + OPTIONAL_GROUPS)}"
        )
    return None


@dataclass(frozen=True)
class Extracted:
    src: str
    dest: str
    instance_id: str = ""
    interface_id: str = ""
    vpc_id: str = ""
    account_id: str = ""
    timestamp: Optional[datetime] = None


@dataclass
class ExtractionCounts:
    lines: int = 0
    extracted: int = 0
    unmatched: int = 0
    too_long: int = 0
    timed_out: int = 0


class Extractor:
    """One compiled pattern, applied line by line, counting what it could not read."""

    def __init__(
        self,
        pattern: str,
        timeout_seconds: float = MATCH_TIMEOUT_SECONDS,
        max_line_length: int = MAX_LINE_LENGTH,
    ) -> None:
        problem = pattern_problem(pattern)
        if problem is not None:
            raise ValueError(f"extraction pattern {problem}")
        self._compiled: Any = regex.compile(normalized(pattern))
        self._timeout = timeout_seconds
        self._max_line_length = max_line_length
        self.counts = ExtractionCounts()

    def extract(self, line: str) -> Optional[Extracted]:
        self.counts.lines += 1
        if len(line) > self._max_line_length:
            self.counts.too_long += 1
            return None
        try:
            found = self._compiled.search(line, timeout=self._timeout)
        except TimeoutError:
            self.counts.timed_out += 1
            return None
        groups = found.groupdict() if found else {}
        src = (groups.get("src") or "").strip()
        dest = (groups.get("dest") or "").strip()
        if not src or not dest or src == "-" or dest == "-":
            self.counts.unmatched += 1
            return None
        self.counts.extracted += 1
        return Extracted(
            src=src,
            dest=dest,
            instance_id=_value(groups.get("instance_id")),
            interface_id=_value(groups.get("interface_id")),
            vpc_id=_value(groups.get("vpc_id")),
            account_id=_value(groups.get("account_id")),
            timestamp=parse_timestamp(groups.get("timestamp")),
        )


def _value(raw: Optional[str]) -> str:
    text = (raw or "").strip()
    return "" if text == "-" else text


def parse_timestamp(raw: Optional[str]) -> Optional[datetime]:
    """An ISO 8601 time, or epoch seconds or milliseconds; None for anything else."""
    text = (raw or "").strip()
    if not text:
        return None
    if text.isdigit():
        value = int(text)
        seconds = value / 1000 if value > 100_000_000_000 else value
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
