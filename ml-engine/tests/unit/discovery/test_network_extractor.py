"""The network extractor and destination matcher, shared by every network source.

Lines are in the shape AWS documents for each preset: Route 53 Resolver query logs as
one JSON object per line (format version 1.100000), VPC Flow Logs in the default
version 2 format. None was captured from a live account: no sandbox credentials were
available, which is why the catalog entry is PREVIEW.
"""

import time
from datetime import datetime, timezone

import pytest

from discovery.network.extractor import (
    MAX_PATTERN_LENGTH,
    PRESETS,
    ROUTE53_RESOLVER_QUERY_LOG,
    VPC_FLOW_LOG_V2,
    Extractor,
    normalized,
    parse_timestamp,
    pattern_problem,
)
from discovery.network.hosts import (
    KNOWN_INFERENCE_HOSTS,
    DestinationMatcher,
    destination_problem,
)

RESOLVER_LINE = (
    '{"version":"1.100000","account_id":"111122223333","region":"us-west-2",'
    '"vpc_id":"vpc-7f3a91c2","query_timestamp":"2026-10-14T05:59:58Z",'
    '"query_name":"bedrock-runtime.us-west-2.amazonaws.com.","query_type":"A",'
    '"query_class":"IN","rcode":"NOERROR","answers":[{"Rdata":"52.94.12.20",'
    '"Type":"A","Class":"IN"}],"srcaddr":"172.31.5.20","srcport":"53744",'
    '"transport":"UDP","srcids":{"instance":"i-0f1e2d3c4b5a69788"}}'
)
# A query forwarded through an inbound Resolver endpoint names the endpoint, not an
# instance.
RESOLVER_ENDPOINT_LINE = (
    '{"version":"1.100000","account_id":"111122223333","region":"us-west-2",'
    '"vpc_id":"vpc-7f3a91c2","query_timestamp":"2026-10-14T06:01:12Z",'
    '"query_name":"api.openai.com.","query_type":"AAAA","query_class":"IN",'
    '"rcode":"NOERROR","answers":[],"srcaddr":"10.20.0.15","srcport":"61022",'
    '"transport":"UDP","srcids":{"resolver_endpoint":"rslvr-in-0123456789abcdef0"}}'
)
FLOW_LINE = (
    "2 111122223333 eni-0a1b2c3d4e5f67890 10.0.1.23 104.18.33.45 49152 443 6 10 840 "
    "1792000000 1792000060 ACCEPT OK"
)
FLOW_NODATA_LINE = (
    "2 111122223333 eni-0a1b2c3d4e5f67890 - - - - - - - 1792000000 1792000060 - NODATA"
)


# -- presets ---------------------------------------------------------------------------


def test_the_resolver_preset_reads_a_query_log_line() -> None:
    line = Extractor(PRESETS[ROUTE53_RESOLVER_QUERY_LOG]).extract(RESOLVER_LINE)
    assert line is not None
    assert (line.src, line.dest) == (
        "172.31.5.20",
        "bedrock-runtime.us-west-2.amazonaws.com.",
    )
    assert (line.instance_id, line.vpc_id, line.account_id) == (
        "i-0f1e2d3c4b5a69788",
        "vpc-7f3a91c2",
        "111122223333",
    )
    assert line.timestamp == datetime(2026, 10, 14, 5, 59, 58, tzinfo=timezone.utc)


def test_the_resolver_preset_holds_any_key_order() -> None:
    reordered = (
        '{"srcids":{"instance":"i-0abc1234def567890"},"srcaddr":"10.0.0.9",'
        '"query_name":"api.anthropic.com.","account_id":"111122223333"}'
    )
    line = Extractor(PRESETS[ROUTE53_RESOLVER_QUERY_LOG]).extract(reordered)
    assert line is not None
    assert (line.src, line.dest, line.instance_id) == (
        "10.0.0.9",
        "api.anthropic.com.",
        "i-0abc1234def567890",
    )
    assert line.vpc_id == "" and line.timestamp is None


def test_a_query_through_a_resolver_endpoint_has_no_instance() -> None:
    line = Extractor(PRESETS[ROUTE53_RESOLVER_QUERY_LOG]).extract(
        RESOLVER_ENDPOINT_LINE
    )
    assert line is not None
    assert line.instance_id == "" and line.src == "10.20.0.15"


def test_the_flow_log_preset_reads_a_v2_line() -> None:
    line = Extractor(PRESETS[VPC_FLOW_LOG_V2]).extract(FLOW_LINE)
    assert line is not None
    assert (line.src, line.dest, line.account_id) == (
        "10.0.1.23",
        "104.18.33.45",
        "111122223333",
    )
    assert line.timestamp == datetime.fromtimestamp(1792000000, tz=timezone.utc)


def test_a_flow_log_line_with_no_data_is_not_traffic() -> None:
    extractor = Extractor(PRESETS[VPC_FLOW_LOG_V2])
    assert extractor.extract(FLOW_NODATA_LINE) is None
    assert extractor.counts.unmatched == 1


@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_every_preset_passes_the_save_time_check(preset: str) -> None:
    assert pattern_problem(PRESETS[preset]) is None


# -- a source's own pattern -------------------------------------------------------------


def test_pcre_named_groups_are_accepted() -> None:
    pattern = r"src=(?<src>\S+) dst=(?<dest>\S+)"
    assert normalized(pattern) == r"src=(?P<src>\S+) dst=(?P<dest>\S+)"
    line = Extractor(pattern).extract("action=allow src=10.1.2.3 dst=api.x.ai")
    assert line is not None and (line.src, line.dest) == ("10.1.2.3", "api.x.ai")


def test_lookbehinds_and_escaped_parens_are_left_alone() -> None:
    assert normalized(r"(?<=a)\(?<x (?<!b)") == r"(?<=a)\(?<x (?<!b)"
    assert normalized(r"\\(?<src>a)") == r"\\(?P<src>a)"


@pytest.mark.parametrize(
    "pattern, problem",
    [
        (r"(?P<src>\S+) (?P<dest", "not a valid regular expression"),
        (r"(?P<src>\S+) \S+", "no named group (?P<dest>...)"),
        (r"(?P<source>\S+) (?P<dest>\S+)", "no named group (?P<src>...)"),
        (r"(?P<src>\S+) (?P<dst>\S+) (?P<dest>\S+)", "named group(s) dst"),
        ("(?P<src>a)(?P<dest>b)" + "x" * MAX_PATTERN_LENGTH, "longer than"),
    ],
)
def test_a_pattern_that_cannot_extract_is_refused(pattern: str, problem: str) -> None:
    found = pattern_problem(pattern)
    assert found is not None and problem in found


def test_a_problem_never_echoes_the_pattern() -> None:
    found = pattern_problem(r"(?P<src>secret-ish) (?P<dest")
    assert found is not None and "secret-ish" not in found


def test_a_pathological_pattern_is_cut_off_per_line_and_counted() -> None:
    extractor = Extractor(r"^(?P<src>a|aa)+(?P<dest>b)$", timeout_seconds=0.02)
    started = time.monotonic()
    assert extractor.extract("a" * 60 + "c") is None
    assert time.monotonic() - started < 2
    assert extractor.counts.timed_out == 1


def test_an_overlong_line_is_skipped_unread() -> None:
    extractor = Extractor(r"(?P<src>\S+) (?P<dest>\S+)", max_line_length=20)
    assert extractor.extract("10.0.0.1 " + "a" * 30) is None
    assert extractor.counts.too_long == 1


@pytest.mark.parametrize(
    "raw, expected",
    [
        (
            "2026-10-14T05:59:58Z",
            datetime(2026, 10, 14, 5, 59, 58, tzinfo=timezone.utc),
        ),
        ("2026-10-14T05:59:58", datetime(2026, 10, 14, 5, 59, 58, tzinfo=timezone.utc)),
        ("1792000000", datetime.fromtimestamp(1792000000, tz=timezone.utc)),
        ("1792000000123", datetime.fromtimestamp(1792000000.123, tz=timezone.utc)),
        ("yesterday", None),
        ("", None),
    ],
)
def test_timestamps_are_iso_or_epoch(raw: str, expected: object) -> None:
    assert parse_timestamp(raw) == expected


# -- destinations ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, provider",
    [
        ("api.openai.com.", "OpenAI"),
        ("API.Anthropic.com", "Anthropic"),
        ("bedrock-runtime.us-east-1.amazonaws.com", "Amazon Bedrock"),
        ("bedrock-agent-runtime.eu-west-1.amazonaws.com", "Amazon Bedrock Agents"),
        ("contoso-east.openai.azure.com", "Azure OpenAI"),
        ("generativelanguage.googleapis.com", "Google Gemini API"),
        ("us-central1-aiplatform.googleapis.com", "Google Vertex AI"),
        ("api.mistral.ai", "Mistral AI"),
        ("api.cohere.com", "Cohere"),
        ("api.cohere.ai", "Cohere"),
        ("api.groq.com", "Groq"),
        ("openrouter.ai", "OpenRouter"),
        ("api.together.xyz", "Together AI"),
        ("api.deepseek.com", "DeepSeek"),
        ("api.x.ai", "xAI"),
        ("api.perplexity.ai", "Perplexity"),
        ("api.fireworks.ai", "Fireworks AI"),
        ("eu.api.openai.com", "OpenAI"),
    ],
)
def test_known_hosts_and_their_subdomains_match_their_provider(
    name: str, provider: str
) -> None:
    match = DestinationMatcher().match(name)
    assert match is not None and match.provider == provider


@pytest.mark.parametrize(
    "name",
    [
        "openai.com",
        "api.openai.com.evil.example",
        "notapi.openai.com.example",
        "openai.azure.com",
        "bedrock.us-east-1.amazonaws.com",
        "bedrock-runtime.amazonaws.com",
        "104.18.33.45",
        "",
    ],
)
def test_lookalikes_neighbours_and_bare_addresses_do_not_match(name: str) -> None:
    assert DestinationMatcher().match(name) is None


def test_extra_hosts_and_ranges_are_matched_by_themselves() -> None:
    matcher = DestinationMatcher(
        ["llm.internal.example.com", "10.50.0.0/16", "fd00::/8"]
    )
    assert matcher.match("gw.llm.internal.example.com") is not None
    ip = matcher.match("10.50.3.4")
    assert ip is not None and ip.provider == "10.50.0.0/16"
    assert matcher.match("fd00::1") is not None
    assert matcher.match("10.51.0.1") is None


def test_the_built_in_list_is_valid_and_has_no_duplicates() -> None:
    patterns = [p for p, _ in KNOWN_INFERENCE_HOSTS]
    assert len(patterns) == len(set(patterns))
    assert all(destination_problem(p) is None for p in patterns)


@pytest.mark.parametrize(
    "entry", ["localhost", "a.*", "a**b.example.com", "sp ace.example.com", "x" * 300]
)
def test_an_entry_that_is_neither_host_nor_range_is_refused(entry: str) -> None:
    assert destination_problem(entry) is not None
