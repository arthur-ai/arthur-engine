"""A CSV file on the engine's own filesystem, one row per discovered agent.

ONE FILE, APPENDED TO. Every scan adds a row per agent it reports, across scans and
restarts, so the same agent appears once per scan; a reader dedupes on `source_id` and
`external_id`, keeping the latest `observed_at`. The header is written once, when the
file is new or empty, and a file that already holds a different header stops the engine
at startup rather than mixing two layouts in one file.

ONLY AGENTS ARE WRITTEN. A scan's outcome is an event of a different shape, so it is
skipped here; the engine logs it to stdout on every scan whatever the destination.

A ROW IS FLAT. Nested values are spread over fixed columns and lists are joined, so the
file opens as a spreadsheet; the JSON destinations carry everything a record holds.
"""

import csv
import logging
import threading
from pathlib import Path
from typing import Any, Literal, Optional, Sequence

from pydantic import ValidationInfo, field_validator

from standalone.config_values import BASE_DIR_CONTEXT, StrictModel, resolve_path
from standalone.sinks.common import (
    DISCOVERED_AGENT_EVENT,
    Event,
    RefusedEvent,
    Sink,
    SinkDeliveryError,
)

# The file's header, in order. Changing it makes every existing file refuse to load,
# so a column is only ever added at the end.
COLUMNS = (
    "observed_at",
    "source_id",
    "source_name",
    "source_vendor",
    "source_config_name",
    "external_id",
    "name",
    "last_seen",
    "runs_on",
    "platform",
    "task_id",
    "creation_source_type",
    "creation_source_vendor",
    "address_instance",
    "address_scope",
    "address_resource_kind",
    "address_resource_id",
    "host_name",
    "host_group",
    "os_version",
    "assigned_user",
    "install_path",
    "version",
    "classification",
    "llm_models",
    "tools",
    "sub_agents",
    "data_sources",
    "network_destinations",
    "identity_basis",
    "permissions",
    "service_names",
)
LIST_SEPARATOR = "; "
# What a spreadsheet reads as the start of a formula. An agent's name and paths come
# from whatever it is installed as, so a cell starting with one is quoted as text.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class CsvDestination(StrictModel):
    type: Literal["csv"]
    # Relative to the config file's directory, as a `{file: ...}` reference is.
    path: str

    @field_validator("path")
    @classmethod
    def _resolve(cls, value: str, info: ValidationInfo) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        base_dir = (info.context or {}).get(BASE_DIR_CONTEXT)
        return str(resolve_path(value, base_dir))

    def build_sink(self, logger: logging.Logger) -> Sink:
        return CsvSink(Path(self.path), logger)


class CsvSink:
    """Implements `Sink` by appending rows to one file.

    ONE SINK SERVES EVERY SCAN, and scans run as threads, so each `send` writes its rows
    under a lock and flushes before releasing it: rows from two scans never interleave,
    and what a scan reports as sent is on disk.
    """

    def __init__(self, path: Path, logger: logging.Logger) -> None:
        self._path = path
        self._lock = threading.Lock()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            _check_header(path)
            self._file = path.open("a", newline="", encoding="utf-8")
        except OSError as e:
            # Raised from the engine's startup, so it stops before any scan runs.
            raise ValueError(
                f"Cannot write the csv destination at {path}: {e.strerror}",
            ) from None
        self._writer = csv.DictWriter(self._file, fieldnames=COLUMNS)
        if self._file.tell() == 0:
            self._writer.writeheader()
            self._file.flush()
        logger.info(f"Appending discovered agents to {path}")

    def send(self, events: Sequence[Event]) -> list[RefusedEvent]:
        """Append a row per agent event; any other event is skipped.

        A file cannot refuse one row, so nothing is returned; a write that fails raises,
        failing the batch.
        """
        rows = [
            _row(e) for e in events if e.get("event_type") == DISCOVERED_AGENT_EVENT
        ]
        if not rows:
            return []
        with self._lock:
            try:
                self._writer.writerows(rows)
                self._file.flush()
            except OSError as e:
                raise SinkDeliveryError(
                    f"Could not write to the csv file at {self._path}: {e.strerror}",
                ) from None
        return []

    def secrets(self) -> tuple[str, ...]:
        return ()

    def close(self) -> None:
        with self._lock:
            self._file.close()


def _check_header(path: Path) -> None:
    """Refuse a file that already starts with another header."""
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        header = next(csv.reader(f), [])
    if tuple(header) != COLUMNS:
        raise ValueError(
            f"{path} already exists with a header that is not the csv destination's "
            f"columns; move it aside or set path to a new file, so rows of two layouts "
            f"are not mixed in one file",
        )


def _row(event: Event) -> dict[str, str]:
    """One agent event as a row, by column. A value the event lacks is an empty cell."""
    source = event.get("source", {})
    agent = event.get("agent", {})
    creation = agent.get("creation_source", {})
    address = creation.get("address", {})
    seen = creation.get("observations", {})
    values = {
        "observed_at": event.get("observed_at"),
        "source_id": source.get("id"),
        "source_name": source.get("name"),
        "source_vendor": source.get("vendor"),
        "source_config_name": source.get("config_name"),
        "external_id": agent.get("external_id"),
        "name": agent.get("name"),
        "last_seen": agent.get("last_seen"),
        "runs_on": agent.get("runs_on"),
        "platform": agent.get("platform"),
        "task_id": agent.get("task_id"),
        "creation_source_type": creation.get("type"),
        "creation_source_vendor": creation.get("vendor"),
        "address_instance": address.get("instance"),
        "address_scope": address.get("scope"),
        "address_resource_kind": address.get("resource_kind"),
        "address_resource_id": address.get("resource_id"),
        "host_name": seen.get("host_name"),
        "host_group": seen.get("host_group"),
        "os_version": seen.get("os_version"),
        "assigned_user": seen.get("assigned_user"),
        "install_path": seen.get("install_path"),
        "version": seen.get("version"),
        "classification": seen.get("classification"),
        "llm_models": _join(agent.get("llm_models"), "name"),
        "tools": _join(agent.get("tools"), "name"),
        "sub_agents": _join(agent.get("sub_agents"), "name"),
        "data_sources": _join(agent.get("data_sources"), "url"),
        "network_destinations": _join(creation.get("destinations"), "host"),
        "identity_basis": creation.get("identity_basis"),
        "permissions": _join(seen.get("permissions")),
        "service_names": _join(seen.get("service_names")),
    }
    return {column: _cell(value) for column, value in values.items()}


def _join(items: Optional[list[Any]], key: Optional[str] = None) -> Optional[str]:
    """A list as one cell: each item's `key`, or the items themselves, joined."""
    if items is None:
        return None
    return LIST_SEPARATOR.join(item[key] if key else item for item in items)


def _cell(value: Optional[str]) -> str:
    if value is None:
        return ""
    return f"'{value}" if value.startswith(FORMULA_PREFIXES) else value
