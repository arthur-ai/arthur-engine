"""The standalone discovery config file: what to scan, how often, and where to send it.

Loaded once at startup and validated whole, so a typo or a missing secret stops the
container before it scans anything rather than surfacing as one source's failed run
six hours later.

SOURCES ARE WRITTEN IN THE PLATFORM'S OWN TYPES. A source is a `PostDiscoverySource` --
name, vendor, and its fields as key/value pairs -- and each query that scans it is a
`DiscoverySourceConfigSpec`, the type a scan job already carries. Nothing here knows
what a Jamf or Vertex source needs: a field the Platform adds is a field this file
accepts, and the connector that reads it is still the only code that checks it. The
one thing the file cannot say that the Platform's type schema does is which fields are
secret, so each connector declares that itself (`SENSITIVE_FIELDS`).

WHERE RESULTS GO IS THE SINK TARGET'S TO SAY. `destination` is validated against the
list of targets in `standalone.sinks`, each of which owns its own config model; nothing
here knows what a Splunk token or a webhook header is.

TWO WAYS TO SUPPLY A VALUE THAT SHOULD NOT LIVE IN THE FILE. Any string may reference
an environment variable as `${NAME}`, and a field's value, a config's query or a
destination secret may be given as `{file: path}` to read it from a mounted file.
Interpolation runs over parsed values rather than the raw text, so a substituted
service account key -- a JSON document full of quotes and newlines -- cannot change how
the YAML around it parses. A file's contents are never interpolated.

NOTHING HERE ECHOES A VALUE BACK. Errors name the field, the variable or the path that
was wrong, never what was in it: pydantic's default message quotes the input, and the
input to a credential field is the credential.
"""

import logging
import math
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Any, Literal, Optional

import yaml
from arthur_client.api_bindings import (
    DiscoveryQueryLanguage,
    DiscoverySourceConfigSpec,
    PostDiscoverySource,
)
from pydantic import (
    BeforeValidator,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from discovery import source_connectors
from standalone.config_values import (
    BASE_DIR_CONTEXT,
    StrictModel,
    read_file_reference,
)
from standalone.sinks import Destination

logger = logging.getLogger(__name__)

# Set to the config file's path to run standalone. Unset, the engine polls the Platform.
DISCOVERY_CONFIG_ENV_VAR = "ML_ENGINE_DISCOVERY_CONFIG"

# Scanning faster than this is a misconfiguration, not a use case: every scan re-reads
# the whole lookback window from the vendor.
MIN_INTERVAL = timedelta(minutes=1)

# Namespace for the IDs minted for sources and configs, which the file does not carry.
# Fixed so the same source has the same ID across restarts and in every event it emits.
_ID_NAMESPACE = uuid.UUID("fb04595b-0284-4c6d-af3c-57dd3e1c5c0e")

# What a config inherits from the source it sits under rather than stating itself.
_DERIVED_CONFIG_KEYS = frozenset({"discovery_source_id", "vendor", "source_fields"})

_ENV_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_DURATION = re.compile(r"^\s*(\d+)\s*([smhd])\s*$")
_DURATION_UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


class StandaloneConfigError(Exception):
    """The config file cannot be used as written. The message says where, not what."""


def _duration(value: Any) -> Any:
    """`90s`, `15m`, `6h`, `1d`, or a number of seconds."""
    if isinstance(value, bool):
        raise ValueError("expected a duration like 15m, 6h or 1d")
    if isinstance(value, (int, float)):
        return timedelta(seconds=value)
    if isinstance(value, str):
        match = _DURATION.match(value)
        if match is None:
            raise ValueError("expected a duration like 15m, 6h or 1d")
        amount, unit = match.groups()
        return timedelta(**{_DURATION_UNITS[unit]: int(amount)})
    return value


Duration = Annotated[timedelta, BeforeValidator(_duration)]


def _id(*parts: str) -> str:
    return str(uuid.uuid5(_ID_NAMESPACE, ":".join(parts)))


def sensitive_fields(vendor: str) -> Optional[frozenset[str]]:
    """The keys the vendor's connector reads as credentials, or None if it never said.

    None is not the empty set: a connector that has not declared its secrets cannot be
    run from a file, because guessing would either hand a credential to the logs as an
    ordinary field or scrub a host name out of the logs as if it were one.
    """
    connector = source_connectors().get(vendor)
    declared = getattr(connector, "SENSITIVE_FIELDS", None)
    return frozenset(declared) if declared is not None else None


# --- Sources -----------------------------------------------------------------------


class StandaloneSource(PostDiscoverySource):  # type: ignore[misc]
    """A `PostDiscoverySource` with the configs that scan it.

    The Platform stores the two apart and joins them by ID; a file nests them instead,
    so each config takes its `discovery_source_id` and `vendor` from the source above
    it. Writing either on a config is refused rather than overridden, so the file never
    says one thing and scans another.
    """

    configs: list[DiscoverySourceConfigSpec] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _configs_inherit_the_source(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        name, vendor, configs = (
            data.get("name"),
            data.get("vendor"),
            data.get("configs"),
        )
        if not (
            isinstance(name, str)
            and isinstance(vendor, str)
            and isinstance(configs, list)
        ):
            return data  # left for field validation to report
        inherited = {"discovery_source_id": _id(vendor, name), "vendor": vendor}
        resolved = []
        for config in configs:
            if isinstance(config, dict):
                derived = sorted(_DERIVED_CONFIG_KEYS & config.keys())
                if derived:
                    raise ValueError(
                        f"{', '.join(derived)} come(s) from the source and cannot be "
                        f"set on one of its configs",
                    )
                config = {**config, **inherited}
            resolved.append(config)
        return {**data, "configs": resolved}

    @model_validator(mode="after")
    def _scannable(self) -> "StandaloneSource":
        vendor = self.vendor.value
        if vendor not in source_connectors():
            raise ValueError(f"this engine has no connector for vendor '{vendor}'")
        if sensitive_fields(vendor) is None:
            raise ValueError(
                f"the '{vendor}' connector does not declare which of its fields are "
                f"secret, so it cannot be configured from a file",
            )
        keys = [f.key for f in self.fields]
        repeated = sorted({key for key in keys if keys.count(key) > 1})
        if repeated:
            raise ValueError(f"field(s) {', '.join(repeated)} are set more than once")
        names = [c.name for c in self.configs]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            raise ValueError(
                f"config name(s) {', '.join(repeated)} are used more than once"
            )
        languages = {language.value for language in DiscoveryQueryLanguage}
        for config in self.configs:
            if config.query_language not in languages:
                raise ValueError(
                    f"config '{config.name}': query_language must be one of "
                    f"{', '.join(sorted(languages))}",
                )
        return self

    def __repr_args__(self) -> Any:
        # The fields hold credentials in plain strings, so a source that is logged or
        # lands in a traceback names its keys and nothing more.
        for name, value in super().__repr_args__():
            if name == "fields":
                value = [f"{f.key}=***" for f in self.fields]
            yield name, value


# --- The file ----------------------------------------------------------------------


class ScheduleConfig(StrictModel):
    interval: Duration
    # Scan once at startup rather than waiting out the first interval.
    run_on_start: bool = True
    # Configs scanned at once. Each (source, config) pair is one scan, as it is one job
    # on the Platform.
    max_concurrent_scans: int = Field(default=1, gt=0)

    @field_validator("interval")
    @classmethod
    def _not_too_often(cls, value: timedelta) -> timedelta:
        if value < MIN_INTERVAL:
            raise ValueError(f"must be at least {MIN_INTERVAL}")
        return value


@dataclass(frozen=True)
class ResolvedScan:
    """One config of one source, as a connector takes it: what a scan job supplies."""

    # The source's name, which the config spec does not carry: the spec names the
    # config, and what the scan reports wants both.
    source_name: str
    discovery_source_config_id: str
    config: DiscoverySourceConfigSpec
    # The config's window rounded up to whole hours, as the Platform dispatches it.
    lookback_hours: int
    source_fields: dict[str, str]
    credentials: dict[str, Optional[str]] = field(repr=False)


class StandaloneDiscoveryConfig(StrictModel):
    version: Literal[1]
    enabled: bool = True
    schedule: ScheduleConfig
    sources: list[StandaloneSource] = Field(min_length=1)
    destination: Destination
    # Send each scan's outcome to the destination too, so a source that stops working
    # is visible where its agents are rather than only in this container's logs.
    emit_scan_outcomes: bool = True

    @model_validator(mode="after")
    def _unique_names(self) -> "StandaloneDiscoveryConfig":
        # A source's name is its identity -- its ID is minted from it -- so two sources
        # sharing one would report as the same source.
        names = [s.name for s in self.sources]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            raise ValueError(
                f"source name(s) {', '.join(repeated)} are used more than once"
            )
        return self

    def scans(self) -> list[ResolvedScan]:
        """Every (source, config) pair, split into what the connector reads."""
        resolved = []
        for source in self.sources:
            secret_keys = sensitive_fields(source.vendor.value) or frozenset()
            source_fields = {
                f.key: f.value for f in source.fields if f.key not in secret_keys
            }
            credentials: dict[str, Optional[str]] = {
                f.key: f.value for f in source.fields if f.key in secret_keys
            }
            for config in source.configs:
                resolved.append(
                    ResolvedScan(
                        source_name=source.name,
                        discovery_source_config_id=_id(
                            config.discovery_source_id,
                            config.name,
                        ),
                        config=config.model_copy(
                            update={"source_fields": source_fields},
                        ),
                        lookback_hours=math.ceil(config.lookback_window_seconds / 3600),
                        source_fields=source_fields,
                        credentials=credentials,
                    ),
                )
        return resolved

    def configs_with_gaps(self) -> list[str]:
        """`source/config` for each config whose window is shorter than the interval.

        Nothing is kept between runs, so whatever a source reported in the gap between
        one scan's window and the next scan is never read. A window of zero or less is a
        full enumeration and has no gap.
        """
        interval = self.schedule.interval.total_seconds()
        return [
            f"{source.name}/{config.name}"
            for source in self.sources
            for config in source.configs
            if 0 < config.lookback_window_seconds < interval
        ]


def standalone_config_path() -> Optional[Path]:
    """The config file this engine was pointed at, or None to run against the Platform."""
    value = os.getenv(DISCOVERY_CONFIG_ENV_VAR, "").strip()
    return Path(value) if value else None


def load_config(path: Path) -> Optional[StandaloneDiscoveryConfig]:
    """The validated config, or None when the file says `enabled: false`.

    A disabled file is not validated past that flag, nor are its `${...}` references
    resolved: switching standalone off should not need the secrets it would have used.
    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise StandaloneConfigError(
            f"Cannot read discovery config {path}: {e.strerror}",
        ) from None
    except UnicodeDecodeError:
        # Read as UTF-8 whatever the locale, as every file the config names is.
        raise StandaloneConfigError(
            f"Discovery config {path} is not valid UTF-8",
        ) from None
    except yaml.YAMLError as e:
        # The mark only, not str(e): that quotes the offending line, and the line may
        # hold an inline secret.
        mark = getattr(e, "problem_mark", None)
        where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        raise StandaloneConfigError(
            f"Discovery config {path} is not valid YAML{where}",
        ) from None

    if not isinstance(raw, dict):
        raise StandaloneConfigError(f"Discovery config {path} must be a YAML mapping")

    enabled = raw.get("enabled", True)
    if not isinstance(enabled, bool):
        raise StandaloneConfigError(
            f"Discovery config {path}: enabled must be true or false",
        )
    if not enabled:
        return None

    missing: list[str] = []
    interpolated = _interpolate(raw, missing)
    if missing:
        raise StandaloneConfigError(
            f"Discovery config {path} references environment variable(s) that are "
            f"not set: {', '.join(sorted(set(missing)))}",
        )
    unreadable = _read_source_files(interpolated, path.parent)
    if unreadable:
        raise StandaloneConfigError(
            f"Discovery config {path} is invalid:\n" + "\n".join(unreadable),
        )

    try:
        config = StandaloneDiscoveryConfig.model_validate(
            interpolated,
            context={BASE_DIR_CONTEXT: path.parent},
        )
    except ValidationError as e:
        raise StandaloneConfigError(
            f"Discovery config {path} is invalid:\n{_describe(e)}",
        ) from None

    gaps = config.configs_with_gaps()
    if gaps:
        logger.warning(
            f"Config(s) {', '.join(gaps)} look back less than the "
            f"{config.schedule.interval} between scans, so agents seen only in the gap "
            f"between windows are missed. Raise lookback_window_seconds to at least "
            f"the interval.",
        )
    return config


def _interpolate(value: Any, missing: list[str]) -> Any:
    """`value` with every `${NAME}` in its strings replaced from the environment."""
    if isinstance(value, dict):
        return {key: _interpolate(item, missing) for key, item in value.items()}
    if isinstance(value, list):
        return [_interpolate(item, missing) for item in value]
    if isinstance(value, str):

        def substitute(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in os.environ:
                missing.append(name)
                return ""
            return os.environ[name]

        return _ENV_REFERENCE.sub(substitute, value)
    return value


def _read_source_files(raw: dict[str, Any], base_dir: Path) -> list[str]:
    """Replace each `{file: path}` field value and query with the file's contents.

    Done before validation, in place on the interpolated copy, because the Platform's
    types take those as plain strings. Returns a line per file that could not be read.
    """
    problems = []
    sources = raw.get("sources")
    for i, source in enumerate(sources if isinstance(sources, list) else []):
        if not isinstance(source, dict):
            continue
        targets = [
            (entry, "value", f"sources.{i}.fields.{j}.value", True)
            for j, entry in enumerate(source.get("fields") or [])
        ] + [
            (entry, "query", f"sources.{i}.configs.{j}.query", False)
            for j, entry in enumerate(source.get("configs") or [])
        ]
        for entry, key, location, strip in targets:
            if isinstance(entry, dict) and isinstance(entry.get(key), dict):
                try:
                    entry[key] = read_file_reference(entry[key], base_dir, strip)
                except ValueError as e:
                    problems.append(f"  {location}: {e}")
    return problems


def _describe(error: ValidationError) -> str:
    """One line per problem, naming the field and never quoting its value."""
    lines = []
    for problem in error.errors(include_input=False, include_url=False):
        location = ".".join(str(part) for part in problem["loc"]) or "<file>"
        lines.append(f"  {location}: {problem['msg']}")
    return "\n".join(lines)
