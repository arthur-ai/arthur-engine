"""The destinations that serve model inference, and how an extracted one is matched.

A HOST PATTERN MATCHES THE NAME AND EVERY NAME UNDER IT. `api.openai.com` matches
`api.openai.com` and `eu.api.openai.com`; a `*` stands for part of one label, so
`*.openai.azure.com` matches a resource name and `bedrock-runtime.*.amazonaws.com` a
region, but `*` never crosses a dot. Names are compared lowercased and without a
trailing dot, which DNS query logs keep.

IP DESTINATIONS MATCH ONLY THE SOURCE'S OWN RANGES. The built-in list is hostnames
because the large providers answer from shared CDN addresses that name nobody in
particular, so a flow log, which carries only addresses, finds inference traffic only
through `extra_inference_hosts` CIDRs a customer knows (a gateway, a private endpoint).

The list is the floor. Each built-in host was checked against the provider's own SDK
base URL or, for AWS, the endpoint rules botocore ships.
"""

import ipaddress
import re
from dataclasses import dataclass
from typing import Iterable, Optional, Union

# (pattern, provider). Order only decides which provider names a host that two patterns
# match, which none of these do.
KNOWN_INFERENCE_HOSTS: tuple[tuple[str, str], ...] = (
    ("api.openai.com", "OpenAI"),
    ("api.anthropic.com", "Anthropic"),
    ("bedrock-runtime.*.amazonaws.com", "Amazon Bedrock"),
    ("bedrock-runtime-fips.*.amazonaws.com", "Amazon Bedrock"),
    ("bedrock-runtime.*.api.aws", "Amazon Bedrock"),
    ("bedrock-agent-runtime.*.amazonaws.com", "Amazon Bedrock Agents"),
    ("bedrock-agent-runtime-fips.*.amazonaws.com", "Amazon Bedrock Agents"),
    ("bedrock-agent-runtime.*.api.aws", "Amazon Bedrock Agents"),
    ("bedrock-agentcore.*.amazonaws.com", "Amazon Bedrock AgentCore"),
    ("*.openai.azure.com", "Azure OpenAI"),
    ("*.services.ai.azure.com", "Azure AI Foundry"),
    ("generativelanguage.googleapis.com", "Google Gemini API"),
    ("aiplatform.googleapis.com", "Google Vertex AI"),
    ("*-aiplatform.googleapis.com", "Google Vertex AI"),
    ("api.mistral.ai", "Mistral AI"),
    ("api.cohere.com", "Cohere"),
    ("api.cohere.ai", "Cohere"),
    ("api.groq.com", "Groq"),
    ("openrouter.ai", "OpenRouter"),
    ("api.together.xyz", "Together AI"),
    ("api.together.ai", "Together AI"),
    ("api.deepseek.com", "DeepSeek"),
    ("api.x.ai", "xAI"),
    ("api.perplexity.ai", "Perplexity"),
    ("api.fireworks.ai", "Fireworks AI"),
)

MAX_EXTRA_DESTINATIONS = 100

# Destinations already decided, so a busy log does not re-match the same host per line.
_CACHE_LIMIT = 50_000

_LABEL = re.compile(r"^(?:[a-z0-9-]*\*[a-z0-9-]*|[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)$")
_ONE_LABEL_PART = "[a-z0-9-]+"

Network = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


@dataclass(frozen=True)
class InferenceDestination:
    """A matched destination: the pattern or range it matched, and who serves it."""

    pattern: str
    provider: str


def _pattern_regex(pattern: str) -> str:
    return r"\.".join(
        _ONE_LABEL_PART.join(re.escape(part) for part in label.split("*"))
        for label in pattern.split(".")
    )


def _network(entry: str) -> Optional[Network]:
    try:
        return ipaddress.ip_network(entry, strict=False)
    except ValueError:
        return None


def destination_problem(entry: str) -> Optional[str]:
    """Why `entry` is neither a host pattern nor an IP address or CIDR, or None."""
    if _network(entry) is not None:
        return None
    labels = entry.split(".")
    if len(labels) < 2:
        return "needs at least two labels, e.g. llm.example.com, or a CIDR"
    if len(entry) > 253:
        return "is longer than a hostname can be"
    if any(label.count("*") > 1 or not _LABEL.match(label) for label in labels):
        return (
            "may hold only letters, digits, '-' and '.', with '*' standing for part of "
            "one label, or be an IP address or CIDR"
        )
    if "*" in labels[-1]:
        return "cannot have '*' in its last label"
    return None


class DestinationMatcher:
    """The built-in hosts plus a source's own hosts and ranges."""

    def __init__(self, extra: Iterable[str] = ()) -> None:
        hosts = list(KNOWN_INFERENCE_HOSTS)
        known = {pattern for pattern, _ in hosts}
        self.networks: list[tuple[Network, InferenceDestination]] = []
        for entry in dict.fromkeys(extra):
            network = _network(entry)
            if network is not None:
                self.networks.append((network, InferenceDestination(entry, entry)))
            elif entry not in known:
                hosts.append((entry, entry))
        self.hosts: tuple[InferenceDestination, ...] = tuple(
            InferenceDestination(p, provider) for p, provider in hosts
        )
        # One alternation finds whether anything matches; the per-host regexes run
        # only for names that do, which are few.
        self._any = re.compile(
            rf"^(?:{_ONE_LABEL_PART}\.)*(?:"
            + "|".join(_pattern_regex(h.pattern) for h in self.hosts)
            + ")$"
        )
        self._each = [
            (re.compile(rf"^(?:{_ONE_LABEL_PART}\.)*{_pattern_regex(h.pattern)}$"), h)
            for h in self.hosts
        ]
        self._cache: dict[str, Optional[InferenceDestination]] = {}

    def match(self, destination: str) -> Optional[InferenceDestination]:
        """What an extracted destination is, or None when it is not inference."""
        name = destination.strip().lower().rstrip(".")
        if name in self._cache:
            return self._cache[name]
        found = self._match(name)
        if len(self._cache) < _CACHE_LIMIT:
            self._cache[name] = found
        return found

    def _match(self, name: str) -> Optional[InferenceDestination]:
        try:
            address = ipaddress.ip_address(name.strip("[]"))
        except ValueError:
            address = None
        if address is not None:
            for network, dest in self.networks:
                if address in network:
                    return dest
            return None
        if not self._any.match(name):
            return None
        for regex, host in self._each:
            if regex.match(name):
                return host
        return None
