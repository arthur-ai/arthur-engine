"""Reading the container's memory limit instead of the host's free memory."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pytest_httpserver import HTTPServer

from memory_limits import (
    ECS_METADATA_URI_ENV,
    MEMORY_LIMIT_SOURCE_ENV,
    ContainerMemory,
    cgroup_memory_limit_bytes,
    cgroup_memory_usage_bytes,
    ecs_task_memory_limit_bytes,
)

MB = 1024 * 1024
GB = 1024 * MB
V1_UNLIMITED = "9223372036854771712\n"


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _host_available(nbytes: int):
    return patch(
        "memory_limits.psutil.virtual_memory",
        return_value=SimpleNamespace(available=nbytes),
    )


def _v2(root: Path, limit: str, current: int, inactive_file: int = 0) -> None:
    _write(root, "memory.max", limit)
    _write(root, "memory.current", f"{current}\n")
    _write(root, "memory.stat", f"anon {current}\ninactive_file {inactive_file}\n")


# Reading the limit


def test_v2_limit(tmp_path: Path) -> None:
    _write(tmp_path, "memory.max", f"{16 * GB}\n")
    assert cgroup_memory_limit_bytes(tmp_path) == 16 * GB


def test_v2_unlimited(tmp_path: Path) -> None:
    _write(tmp_path, "memory.max", "max\n")
    assert cgroup_memory_limit_bytes(tmp_path) is None


def test_v1_takes_the_lower_of_own_and_hierarchical_limit(tmp_path: Path) -> None:
    # A container without its own limit inside a task-level limit, as on ECS.
    _write(tmp_path, "memory/memory.limit_in_bytes", V1_UNLIMITED)
    _write(
        tmp_path,
        "memory/memory.stat",
        f"cache 0\nhierarchical_memory_limit {16 * GB}\ntotal_inactive_file 0\n",
    )
    assert cgroup_memory_limit_bytes(tmp_path) == 16 * GB


def test_v1_unlimited(tmp_path: Path) -> None:
    _write(tmp_path, "memory/memory.limit_in_bytes", V1_UNLIMITED)
    _write(tmp_path, "memory/memory.stat", f"hierarchical_memory_limit {V1_UNLIMITED}")
    assert cgroup_memory_limit_bytes(tmp_path) is None


def test_unreadable_or_garbled_files_mean_no_limit(tmp_path: Path) -> None:
    assert cgroup_memory_limit_bytes(tmp_path) is None
    assert cgroup_memory_usage_bytes(tmp_path) is None
    _write(tmp_path, "memory.max", "not a number\n")
    assert cgroup_memory_limit_bytes(tmp_path) is None


def test_usage_excludes_inactive_file_pages(tmp_path: Path) -> None:
    _v2(tmp_path, "max", current=3 * GB, inactive_file=1 * GB)
    assert cgroup_memory_usage_bytes(tmp_path) == 2 * GB


def test_v1_usage_excludes_inactive_file_pages(tmp_path: Path) -> None:
    _write(tmp_path, "memory/memory.usage_in_bytes", f"{3 * GB}\n")
    _write(tmp_path, "memory/memory.stat", f"total_inactive_file {1 * GB}\n")
    assert cgroup_memory_usage_bytes(tmp_path) == 2 * GB


def test_ecs_task_limit(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/v4/abc/task").respond_with_json(
        {"Limits": {"CPU": 2, "Memory": 16384}},
    )
    assert ecs_task_memory_limit_bytes(httpserver.url_for("/v4/abc")) == 16 * GB


def test_ecs_task_limit_failure_is_no_limit(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/v4/abc/task").respond_with_data("", status=500)
    assert ecs_task_memory_limit_bytes(httpserver.url_for("/v4/abc")) is None
    assert ecs_task_memory_limit_bytes(None) is None


# Choosing a limit


def test_detect_takes_the_lowest_limit(httpserver: HTTPServer, tmp_path: Path) -> None:
    # A cgroup v2 container on ECS that cannot see the task-level limit.
    _v2(tmp_path, "max\n", current=1 * GB)
    httpserver.expect_request("/v4/abc/task").respond_with_json(
        {"Limits": {"Memory": 16384}},
    )
    memory = ContainerMemory.detect(
        tmp_path,
        {ECS_METADATA_URI_ENV: httpserver.url_for("/v4/abc")},
    )
    assert (memory.limit_bytes, memory.source) == (16 * GB, "ECS task metadata")


def test_detect_without_any_limit_is_the_host(tmp_path: Path) -> None:
    memory = ContainerMemory.detect(tmp_path, {})
    assert memory.limit_bytes is None
    with _host_available(30 * GB):
        assert memory.available_mb() == 30 * 1024


def test_host_mode_ignores_the_container_limit(tmp_path: Path) -> None:
    _v2(tmp_path, f"{16 * GB}\n", current=1 * GB)
    memory = ContainerMemory.detect(tmp_path, {MEMORY_LIMIT_SOURCE_ENV: "host"})
    assert memory.limit_bytes is None
    with _host_available(30 * GB):
        assert memory.available_mb() == 30 * 1024


def test_unknown_mode_uses_the_container_limit(tmp_path: Path) -> None:
    _v2(tmp_path, f"{16 * GB}\n", current=0)
    memory = ContainerMemory.detect(tmp_path, {MEMORY_LIMIT_SOURCE_ENV: "bogus"})
    assert memory.limit_bytes == 16 * GB


# Free memory


def test_available_is_capped_by_the_limit_when_the_host_has_more(
    tmp_path: Path,
) -> None:
    # The host has 30 GB free, the container may use 16 GB and already uses 1 GB.
    _v2(tmp_path, f"{16 * GB}\n", current=1 * GB)
    with _host_available(30 * GB):
        assert ContainerMemory.detect(tmp_path, {}).available_mb() == 15 * 1024


def test_available_is_the_host_when_it_has_less(tmp_path: Path) -> None:
    _v2(tmp_path, f"{16 * GB}\n", current=0)
    with _host_available(4 * GB):
        assert ContainerMemory.detect(tmp_path, {}).available_mb() == 4 * 1024


def test_available_is_never_negative(tmp_path: Path) -> None:
    _v2(tmp_path, f"{1 * GB}\n", current=2 * GB)
    with _host_available(30 * GB):
        assert ContainerMemory.detect(tmp_path, {}).available_mb() == 0


def test_usage_falls_back_to_the_process_tree_when_unreadable(tmp_path: Path) -> None:
    memory = ContainerMemory(16 * GB, "ECS task metadata", tmp_path)
    with (
        _host_available(30 * GB),
        patch(
            "memory_limits._process_tree_rss_bytes",
            return_value=2 * GB,
        ),
    ):
        assert memory.available_mb() == 14 * 1024
