"""Memory the container may use, as opposed to memory the host has.

psutil reads /proc/meminfo, which inside a container describes the host or VM, not
the container's memory limit. On a host with more memory than the limit, that would
let the agent accept jobs whose memory requirements add up to more than the limit,
and the kernel kills the container (or its largest job process) once they use it.

The limit is taken as the lowest of the limits that can be read:
- cgroup v2: memory.max of the container's cgroup.
- cgroup v1: memory.limit_in_bytes, and the hierarchical_memory_limit in memory.stat,
  which also covers a limit set on a parent cgroup (e.g. a task-level limit around a
  container that has none of its own).
- ECS: the task's memory limit from the task metadata endpoint, for when the task
  limit sits on a parent cgroup that a cgroup v2 container cannot see.
With no limit to read, or with ML_ENGINE_MEMORY_LIMIT_SOURCE=host, it is the host's
available memory, exactly as before.
"""

import json
import logging
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import psutil

logger = logging.getLogger()

CGROUP_ROOT = Path("/sys/fs/cgroup")
MEMORY_LIMIT_SOURCE_ENV = "ML_ENGINE_MEMORY_LIMIT_SOURCE"
ECS_METADATA_URI_ENV = "ECS_CONTAINER_METADATA_URI_V4"
# cgroup v1 reports "no limit" as a page-aligned value close to 2**63.
_V1_UNLIMITED_THRESHOLD = 1 << 60
_ECS_METADATA_TIMEOUT_SECONDS = 2
_MB = 1024 * 1024


def _read_int(path: Path) -> int | None:
    try:
        text = path.read_text().strip()
    except OSError:
        return None
    if text == "max":
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _read_stat(stat_path: Path, key: str) -> int | None:
    try:
        lines = stat_path.read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        name, _, value = line.partition(" ")
        if name == key:
            try:
                return int(value)
            except ValueError:
                return None
    return None


def cgroup_memory_limit_bytes(root: Path = CGROUP_ROOT) -> int | None:
    """The cgroup's memory limit in bytes, or None when there is none to read."""
    v2_limit = _read_int(root / "memory.max")
    if v2_limit is not None:
        return v2_limit
    v1_limits = [
        limit
        for limit in (
            _read_int(root / "memory" / "memory.limit_in_bytes"),
            _read_stat(root / "memory" / "memory.stat", "hierarchical_memory_limit"),
        )
        if limit is not None and limit < _V1_UNLIMITED_THRESHOLD
    ]
    return min(v1_limits) if v1_limits else None


def cgroup_memory_usage_bytes(root: Path = CGROUP_ROOT) -> int | None:
    """Memory the cgroup is charged for, less the page cache it can drop first.

    The cgroup's charge includes cached file pages (e.g. files a job has read), which
    the kernel reclaims before it kills anything, so like `docker stats` the inactive
    file pages are not counted. None when the usage cannot be read.
    """
    usage = _read_int(root / "memory.current")
    inactive_file = _read_stat(root / "memory.stat", "inactive_file")
    if usage is None:
        usage = _read_int(root / "memory" / "memory.usage_in_bytes")
        inactive_file = _read_stat(
            root / "memory" / "memory.stat",
            "total_inactive_file",
        )
    if usage is None:
        return None
    return max(usage - (inactive_file or 0), 0)


def ecs_task_memory_limit_bytes(metadata_uri: str | None) -> int | None:
    """The ECS task's memory limit, or None off ECS or when the endpoint fails."""
    if not metadata_uri:
        return None
    try:
        with urllib.request.urlopen(
            f"{metadata_uri}/task",
            timeout=_ECS_METADATA_TIMEOUT_SECONDS,
        ) as response:
            limit_mb = json.load(response).get("Limits", {}).get("Memory")
    except Exception:
        logger.warning("Could not read the task memory limit from ECS", exc_info=True)
        return None
    if not isinstance(limit_mb, (int, float)) or limit_mb <= 0:
        return None
    return int(limit_mb) * _MB


def _process_tree_rss_bytes() -> int:
    """This process and its children, for when the cgroup's usage cannot be read."""
    process = psutil.Process()
    total = 0
    for p in [process, *process.children(recursive=True)]:
        try:
            total += p.memory_info().rss
        except psutil.Error:
            continue
    return total


def _host_available_bytes() -> int:
    return psutil.virtual_memory().available


@dataclass(frozen=True)
class ContainerMemory:
    """The container's memory limit, read once, and its free memory, read on demand."""

    limit_bytes: int | None
    source: str
    cgroup_root: Path = CGROUP_ROOT

    @classmethod
    def detect(
        cls,
        cgroup_root: Path = CGROUP_ROOT,
        environ: Mapping[str, str] = os.environ,
    ) -> "ContainerMemory":
        mode = environ.get(MEMORY_LIMIT_SOURCE_ENV, "container").strip().lower()
        if mode == "host":
            return cls(None, f"host ({MEMORY_LIMIT_SOURCE_ENV}=host)", cgroup_root)
        if mode != "container":
            logger.warning(
                f"Unknown {MEMORY_LIMIT_SOURCE_ENV}={mode!r}; using the container limit",
            )
        limits = {
            "cgroup": cgroup_memory_limit_bytes(cgroup_root),
            "ECS task metadata": ecs_task_memory_limit_bytes(
                environ.get(ECS_METADATA_URI_ENV),
            ),
        }
        known = {name: limit for name, limit in limits.items() if limit is not None}
        if not known:
            return cls(None, "host (no container limit found)", cgroup_root)
        source = min(known, key=lambda name: known[name])
        return cls(known[source], source, cgroup_root)

    def usage_bytes(self) -> int:
        usage = cgroup_memory_usage_bytes(self.cgroup_root)
        return usage if usage is not None else _process_tree_rss_bytes()

    def host_available_mb(self) -> int:
        return _host_available_bytes() // _MB

    def available_mb(self) -> int:
        """Free memory as the container sees it: the host's, capped by the limit."""
        host_available = _host_available_bytes()
        if self.limit_bytes is None:
            return host_available // _MB
        headroom = max(self.limit_bytes - self.usage_bytes(), 0)
        return min(host_available, headroom) // _MB
