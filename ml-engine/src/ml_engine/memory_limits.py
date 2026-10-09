"""Memory the container may use, as opposed to memory the host has.

psutil reads /proc/meminfo, which inside a container describes the host or VM, not
the container's memory limit. On a host with more memory than the limit, that would
let the agent accept jobs whose memory requirements add up to more than the limit,
and the kernel kills the container (or its largest job process) once they use it.

The limits come from the cgroup hierarchy, which every container runtime uses (Docker,
containerd under Kubernetes, ECS on EC2 and Fargate):
- The process's own cgroup is found through /proc/self/cgroup, and it and each
  ancestor visible under /sys/fs/cgroup is checked, because a limit can sit on a
  parent (a Kubernetes pod, an ECS task) rather than on the container itself.
- cgroup v2 (unified hierarchy): memory.max and memory.current at each level.
- cgroup v1: the memory controller's memory.limit_in_bytes and memory.usage_in_bytes
  at each level, plus hierarchical_memory_limit, the effective limit of all ancestors.
On ECS only (ECS_CONTAINER_METADATA_URI_V4 set), the task's memory limit from the task
metadata endpoint is also read, for a task-level limit on a parent cgroup the container
cannot see. Being the task's limit, it is set against the task's usage: this container's
plus the other containers' from the task stats endpoint. It is never required: any
failure means no limit from that source, or no other usage counted.

The headroom is the smallest (limit - usage) over every level that has a limit, capped
by the host's available memory. With no limit anywhere, or with
ML_ENGINE_MEMORY_LIMIT_SOURCE=host, it is the host's available memory, as before.
"""

import json
import logging
import os
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import psutil

logger = logging.getLogger()

CGROUP_ROOT = Path("/sys/fs/cgroup")
PROC_SELF_CGROUP = Path("/proc/self/cgroup")
MEMORY_LIMIT_SOURCE_ENV = "ML_ENGINE_MEMORY_LIMIT_SOURCE"
ECS_METADATA_URI_ENV = "ECS_CONTAINER_METADATA_URI_V4"
# cgroup v1 reports "no limit" as a page-aligned value close to 2**63.
_V1_UNLIMITED_THRESHOLD = 1 << 60
_ECS_METADATA_TIMEOUT_SECONDS = 1
# How long other containers' usage from ECS task stats is reused before re-reading.
_ECS_STATS_TTL_SECONDS = 10
_MB = 1024 * 1024


def _read_int(path: Path) -> int | None:
    try:
        text = path.read_text().strip()
    except OSError:
        return None
    if text == "max":
        return None
    try:
        value = int(text)
    except ValueError:
        return None
    return value if 0 <= value < _V1_UNLIMITED_THRESHOLD else None


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


@dataclass(frozen=True)
class CgroupLevel:
    """One directory of the cgroup hierarchy and how to read its memory files."""

    path: Path
    version: int

    def limit_bytes(self) -> int | None:
        if self.version == 2:
            limit = _read_int(self.path / "memory.max")
            return limit if limit else None
        limits = [
            limit
            for limit in (
                _read_int(self.path / "memory.limit_in_bytes"),
                _read_stat(self.path / "memory.stat", "hierarchical_memory_limit"),
            )
            if limit is not None and 0 < limit < _V1_UNLIMITED_THRESHOLD
        ]
        return min(limits) if limits else None

    def usage_bytes(self) -> int | None:
        """Memory charged to this level, less the page cache it can drop first.

        The charge includes cached file pages (e.g. files a job has read), which the
        kernel reclaims before it kills anything, so like `docker stats` the inactive
        file pages are not counted. None when the usage cannot be read.
        """
        if self.version == 2:
            usage = _read_int(self.path / "memory.current")
            inactive_file = _read_stat(self.path / "memory.stat", "inactive_file")
        else:
            usage = _read_int(self.path / "memory.usage_in_bytes")
            inactive_file = _read_stat(
                self.path / "memory.stat",
                "total_inactive_file",
            )
        if usage is None:
            return None
        return max(usage - (inactive_file or 0), 0)


def _own_cgroup_path(proc_cgroup: Path, version: int) -> str:
    """This process's cgroup path from /proc/self/cgroup, or "/" if unknown."""
    try:
        lines = proc_cgroup.read_text().splitlines()
    except OSError:
        return "/"
    for line in lines:
        hierarchy_id, _, rest = line.partition(":")
        controllers, _, path = rest.partition(":")
        if version == 2 and hierarchy_id == "0" and controllers == "":
            return path or "/"
        if version == 1 and "memory" in controllers.split(","):
            return path or "/"
    return "/"


def cgroup_levels(
    root: Path = CGROUP_ROOT,
    proc_cgroup: Path = PROC_SELF_CGROUP,
) -> list[CgroupLevel]:
    """The process's own cgroup, then each ancestor visible under the mount.

    Empty when no cgroup filesystem with a memory controller is mounted. Inside a
    container with its own cgroup namespace /proc/self/cgroup says "/", and the mount
    root is the container's own cgroup. When the path it gives does not exist under
    the mount (the host's path for a cgroup mounted at its own directory), the mount
    root is used.
    """
    if (root / "cgroup.controllers").exists():
        version, mount = 2, root
    elif (root / "memory").is_dir():
        version, mount = 1, root / "memory"
    else:
        return []
    own = mount / _own_cgroup_path(proc_cgroup, version).lstrip("/")
    if not own.is_dir():
        own = mount
    levels = [CgroupLevel(own, version)]
    current = own
    while current != mount and mount in current.parents:
        current = current.parent
        levels.append(CgroupLevel(current, version))
    return levels


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


def _get_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=_ECS_METADATA_TIMEOUT_SECONDS) as response:
        return json.load(response)


def _docker_stats_usage_bytes(stats: object) -> int:
    """Usage from one container's docker-format stats, less inactive file pages."""
    if not isinstance(stats, dict):
        return 0
    memory = stats.get("memory_stats") or {}
    usage = memory.get("usage") or 0
    detail = memory.get("stats") or {}
    inactive = detail.get("inactive_file", detail.get("total_inactive_file", 0)) or 0
    return max(int(usage) - int(inactive), 0)


@dataclass
class EcsTaskStats:
    """Memory used by the task's other containers, which share the task's limit.

    Read from the task stats endpoint and reused for a few seconds, since the agent
    asks for free memory several times a second. Any failure counts as 0, which is
    the same as not knowing about the other containers at all.
    """

    metadata_uri: str
    _own_docker_id: str | None = None
    _value: int = 0
    _read_at: float | None = None

    def other_containers_usage_bytes(self) -> int:
        now = time.monotonic()
        if self._read_at is not None and now - self._read_at < _ECS_STATS_TTL_SECONDS:
            return self._value
        self._read_at = now
        try:
            if self._own_docker_id is None:
                own = _get_json(self.metadata_uri)
                self._own_docker_id = (
                    own.get("DockerId") if isinstance(own, dict) else None
                )
            stats = _get_json(f"{self.metadata_uri}/task/stats")
        except Exception:
            logger.warning("Could not read ECS task stats", exc_info=True)
            self._value = 0
            return 0
        if not isinstance(stats, dict) or self._own_docker_id is None:
            self._value = 0
            return 0
        self._value = sum(
            _docker_stats_usage_bytes(container_stats)
            for docker_id, container_stats in stats.items()
            if docker_id != self._own_docker_id
        )
        return self._value


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
    """The container's memory limits, found once, and its headroom, read on demand.

    `limited_levels` are the cgroup levels that had a limit at startup; `ecs_limit_bytes`
    is the ECS task limit when on ECS. That limit is the task's, so it is set against
    the task's usage: this container's own cgroup (`own_level`) plus the other
    containers' usage from the task stats (`ecs_task_stats`).
    """

    source: str
    limited_levels: tuple[CgroupLevel, ...] = ()
    ecs_limit_bytes: int | None = None
    own_level: CgroupLevel | None = None
    ecs_task_stats: EcsTaskStats | None = field(default=None, compare=False)

    @classmethod
    def detect(
        cls,
        cgroup_root: Path = CGROUP_ROOT,
        environ: Mapping[str, str] = os.environ,
        proc_cgroup: Path = PROC_SELF_CGROUP,
    ) -> "ContainerMemory":
        mode = environ.get(MEMORY_LIMIT_SOURCE_ENV, "container").strip().lower()
        if mode == "host":
            return cls(source=f"host ({MEMORY_LIMIT_SOURCE_ENV}=host)")
        if mode != "container":
            logger.warning(
                f"Unknown {MEMORY_LIMIT_SOURCE_ENV}={mode!r}; using the container limit",
            )
        levels = cgroup_levels(cgroup_root, proc_cgroup)
        limited = tuple(level for level in levels if level.limit_bytes() is not None)
        ecs_uri = environ.get(ECS_METADATA_URI_ENV)
        ecs_limit = ecs_task_memory_limit_bytes(ecs_uri)
        sources = []
        if limited:
            sources.append(f"cgroup v{limited[0].version}")
        if ecs_limit is not None:
            sources.append("ECS task metadata")
        if not sources:
            return cls(source="host (no container limit found)")
        return cls(
            source=" + ".join(sources),
            limited_levels=limited,
            ecs_limit_bytes=ecs_limit,
            own_level=levels[0] if levels else None,
            ecs_task_stats=(
                EcsTaskStats(ecs_uri) if ecs_uri and ecs_limit is not None else None
            ),
        )

    @property
    def limit_bytes(self) -> int | None:
        """The lowest limit found, for logging; None when there is none."""
        limits = [
            limit
            for limit in [
                *(level.limit_bytes() for level in self.limited_levels),
                self.ecs_limit_bytes,
            ]
            if limit is not None
        ]
        return min(limits) if limits else None

    def _own_usage_bytes(self) -> int:
        usage = self.own_level.usage_bytes() if self.own_level else None
        return usage if usage is not None else _process_tree_rss_bytes()

    def headroom_bytes(self) -> int | None:
        """The smallest (limit - usage) over every limit, or None with no limit."""
        headrooms = []
        for level in self.limited_levels:
            limit = level.limit_bytes()
            if limit is None:
                continue
            usage = level.usage_bytes()
            if usage is None:
                usage = _process_tree_rss_bytes()
            headrooms.append(limit - usage)
        if self.ecs_limit_bytes is not None:
            task_usage = self._own_usage_bytes()
            if self.ecs_task_stats is not None:
                task_usage += self.ecs_task_stats.other_containers_usage_bytes()
            headrooms.append(self.ecs_limit_bytes - task_usage)
        return max(min(headrooms), 0) if headrooms else None

    def host_available_mb(self) -> int:
        return _host_available_bytes() // _MB

    def available_mb(self) -> int:
        """Free memory as the container sees it: the host's, capped by the limits."""
        host_available = _host_available_bytes()
        headroom = self.headroom_bytes()
        if headroom is None:
            return host_available // _MB
        return min(host_available, headroom) // _MB
