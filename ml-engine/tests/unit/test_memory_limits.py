"""Reading the container's memory limit instead of the host's free memory.

Each test lays out the files a real deployment shows the process: /sys/fs/cgroup and
/proc/self/cgroup. The layouts follow what each runtime mounts by default.
"""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pytest_httpserver import HTTPServer

from memory_limits import (
    ECS_METADATA_URI_ENV,
    MEMORY_LIMIT_SOURCE_ENV,
    CgroupLevel,
    ContainerMemory,
    EcsTaskStats,
    cgroup_levels,
    ecs_task_memory_limit_bytes,
)

MB = 1024 * 1024
GB = 1024 * MB
V1_UNLIMITED = "9223372036854771712"


class Layout:
    """A fake /sys/fs/cgroup and /proc/self/cgroup under a temporary directory."""

    def __init__(self, tmp_path: Path, proc_cgroup: str) -> None:
        self.root = tmp_path / "sys" / "fs" / "cgroup"
        self.root.mkdir(parents=True)
        self.proc = tmp_path / "proc_self_cgroup"
        self.proc.write_text(proc_cgroup)

    def v2(self, rel: str = "", **files: str) -> Path:
        (self.root / "cgroup.controllers").write_text("cpu memory pids\n")
        return self._files(self.root / rel, files)

    def v1(self, rel: str = "", **files: str) -> Path:
        return self._files(self.root / "memory" / rel, files)

    @staticmethod
    def _files(directory: Path, files: dict[str, str]) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (directory / name.replace("__", ".")).write_text(text + "\n")
        return directory

    def detect(self, environ: dict[str, str] | None = None) -> ContainerMemory:
        return ContainerMemory.detect(self.root, environ or {}, self.proc)


def _host_available(nbytes: int):
    return patch(
        "memory_limits.psutil.virtual_memory",
        return_value=SimpleNamespace(available=nbytes),
    )


def _stat_v2(inactive_file: int = 0) -> str:
    return f"anon 0\ninactive_file {inactive_file}"


# Deployments


def test_docker_compose_without_a_limit_is_the_host(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max="max", memory__current=str(1 * GB))
    memory = layout.detect()
    assert memory.limit_bytes is None
    assert memory.source == "host (no container limit found)"
    with _host_available(30 * GB):
        assert memory.available_mb() == 30 * 1024


def test_docker_with_a_memory_limit(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(
        memory__max=str(8 * GB),
        memory__current=str(1 * GB),
        memory__stat=_stat_v2(),
    )
    memory = layout.detect()
    assert (memory.source, memory.limit_bytes) == ("cgroup v2", 8 * GB)
    with _host_available(12 * GB):
        assert memory.available_mb() == 7 * 1024


def test_kubernetes_v2_container_limit_in_its_own_namespace(tmp_path: Path) -> None:
    # GKE COS / containerd: the container sees its own cgroup at the mount root.
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max=str(16 * GB), memory__current=str(1 * GB))
    with _host_available(30 * GB):
        assert layout.detect().available_mb() == 15 * 1024


def test_kubernetes_v2_pod_limit_with_a_sidecar_seen_from_the_host_namespace(
    tmp_path: Path,
) -> None:
    pod = "kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod1.slice"
    container = f"{pod}/cri-containerd-abc.scope"
    layout = Layout(tmp_path, f"0::/{container}\n")
    layout.v2()
    # The container has no limit of its own; the pod has 16 GB, a sidecar uses 3 GB.
    layout.v2(container, memory__max="max", memory__current=str(1 * GB))
    layout.v2(pod, memory__max=str(16 * GB), memory__current=str(4 * GB))
    memory = layout.detect()
    assert (memory.source, memory.limit_bytes) == ("cgroup v2", 16 * GB)
    with _host_available(30 * GB):
        assert memory.available_mb() == 12 * 1024


def test_kubernetes_v2_container_limit_below_the_pod_limit(tmp_path: Path) -> None:
    pod = "kubepods.slice/kubepods-pod1.slice"
    container = f"{pod}/cri-containerd-abc.scope"
    layout = Layout(tmp_path, f"0::/{container}\n")
    layout.v2()
    layout.v2(container, memory__max=str(4 * GB), memory__current=str(1 * GB))
    layout.v2(pod, memory__max=str(16 * GB), memory__current=str(1 * GB))
    with _host_available(30 * GB):
        assert layout.detect().available_mb() == 3 * 1024


def test_fargate_v1_task_limit_on_a_parent_cgroup(tmp_path: Path) -> None:
    # The container has no limit; the task's limit shows as the hierarchical limit.
    # /proc/self/cgroup gives the host's path, which does not exist under a mount
    # of the container's own directory, so the mount root is read.
    layout = Layout(tmp_path, "11:memory:/ecs/task1/container1\n")
    layout.v1(
        memory__limit_in_bytes=V1_UNLIMITED,
        memory__usage_in_bytes=str(2 * GB),
        memory__stat=f"hierarchical_memory_limit {16 * GB}\ntotal_inactive_file {GB}",
    )
    memory = layout.detect()
    assert (memory.source, memory.limit_bytes) == ("cgroup v1", 16 * GB)
    with _host_available(30 * GB):
        assert memory.available_mb() == 15 * 1024


def test_fargate_v2_without_a_visible_limit_uses_ecs_metadata(
    tmp_path: Path,
    httpserver: HTTPServer,
) -> None:
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max="max", memory__current=str(1 * GB))
    httpserver.expect_request("/v4/c1/task").respond_with_json(
        {"Limits": {"CPU": 2, "Memory": 16384}},
    )
    memory = layout.detect({ECS_METADATA_URI_ENV: httpserver.url_for("/v4/c1")})
    assert (memory.source, memory.limit_bytes) == ("ECS task metadata", 16 * GB)
    with _host_available(30 * GB):
        assert memory.available_mb() == 15 * 1024


def test_ecs_on_ec2_v2_task_limit_on_a_visible_parent(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "0::/ecs/task1/container1\n")
    layout.v2()
    layout.v2("ecs/task1/container1", memory__max="max", memory__current=str(GB))
    layout.v2("ecs/task1", memory__max=str(4 * GB), memory__current=str(GB))
    with _host_available(30 * GB):
        assert layout.detect().available_mb() == 3 * 1024


def test_cgroup_v1_host_with_a_container_limit(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "11:cpuset:/\n10:memory,hugetlb:/\n")
    layout.v1(
        memory__limit_in_bytes=str(8 * GB),
        memory__usage_in_bytes=str(1 * GB),
        memory__stat=f"hierarchical_memory_limit {8 * GB}\ntotal_inactive_file 0",
    )
    with _host_available(30 * GB):
        assert layout.detect().available_mb() == 7 * 1024


def test_cgroup_v1_unlimited_is_the_host(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "10:memory:/\n")
    layout.v1(
        memory__limit_in_bytes=V1_UNLIMITED,
        memory__stat=f"hierarchical_memory_limit {V1_UNLIMITED}",
    )
    assert layout.detect().limit_bytes is None


def test_no_cgroup_filesystem_is_the_host(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "")
    assert cgroup_levels(layout.root, layout.proc) == []
    memory = layout.detect()
    assert memory.limit_bytes is None
    with _host_available(30 * GB):
        assert memory.available_mb() == 30 * 1024


# Fallbacks


def test_unreadable_garbled_and_zero_files_are_no_limit(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "0::/\n")
    level = layout.v2(memory__max="not a number")
    assert CgroupLevel(level, 2).limit_bytes() is None
    (level / "memory.max").write_text("0\n")
    assert CgroupLevel(level, 2).limit_bytes() is None
    (level / "memory.max").write_text(f"{GB}\n")
    if os.geteuid() != 0:  # root reads files regardless of their mode
        (level / "memory.max").chmod(0)
        assert CgroupLevel(level, 2).limit_bytes() is None


def test_missing_proc_self_cgroup_reads_the_mount_root(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "")
    layout.proc.unlink()
    layout.v2(memory__max=str(8 * GB), memory__current="0")
    assert layout.detect().limit_bytes == 8 * GB


def test_usage_excludes_inactive_file_pages(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "0::/\n")
    level = layout.v2(
        memory__current=str(3 * GB),
        memory__stat=_stat_v2(inactive_file=GB),
    )
    assert CgroupLevel(level, 2).usage_bytes() == 2 * GB


def test_unreadable_usage_falls_back_to_the_process_tree(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max=str(16 * GB))
    with (
        _host_available(30 * GB),
        patch(
            "memory_limits._process_tree_rss_bytes",
            return_value=2 * GB,
        ),
    ):
        assert layout.detect().available_mb() == 14 * 1024


def test_headroom_is_never_negative(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max=str(GB), memory__current=str(2 * GB))
    with _host_available(30 * GB):
        assert layout.detect().available_mb() == 0


def test_the_host_caps_the_headroom_when_it_has_less(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max=str(16 * GB), memory__current="0")
    with _host_available(4 * GB):
        assert layout.detect().available_mb() == 4 * 1024


# ECS metadata is optional


def test_ecs_metadata_is_not_consulted_off_ecs(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max=str(8 * GB), memory__current="0")
    with patch("memory_limits.urllib.request.urlopen") as urlopen:
        assert layout.detect().source == "cgroup v2"
    urlopen.assert_not_called()


def test_ecs_metadata_failures_are_never_required(
    tmp_path: Path,
    httpserver: HTTPServer,
) -> None:
    httpserver.expect_request("/v4/c1/task").respond_with_data("", status=500)
    assert ecs_task_memory_limit_bytes(httpserver.url_for("/v4/c1")) is None
    httpserver.expect_request("/v4/c2/task").respond_with_json({"Limits": {}})
    assert ecs_task_memory_limit_bytes(httpserver.url_for("/v4/c2")) is None
    # Nothing listening: fails fast instead of hanging startup.
    assert ecs_task_memory_limit_bytes("http://127.0.0.1:9/v4/c3") is None

    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max=str(8 * GB), memory__current="0")
    memory = layout.detect({ECS_METADATA_URI_ENV: httpserver.url_for("/v4/c1")})
    assert (memory.source, memory.limit_bytes) == ("cgroup v2", 8 * GB)


def test_cgroup_and_ecs_limits_together_take_the_lower(
    tmp_path: Path,
    httpserver: HTTPServer,
) -> None:
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max=str(4 * GB), memory__current="0")
    httpserver.expect_request("/v4/c1/task").respond_with_json(
        {"Limits": {"Memory": 16384}},
    )
    memory = layout.detect({ECS_METADATA_URI_ENV: httpserver.url_for("/v4/c1")})
    assert memory.source == "cgroup v2 + ECS task metadata"
    assert memory.limit_bytes == 4 * GB


def test_fargate_v2_ecs_limit_counts_a_sidecars_usage(
    tmp_path: Path,
    httpserver: HTTPServer,
) -> None:
    # The task limit covers every container in the task, so a sidecar's usage
    # (here 3 GB, 1 GB of it reclaimable cache) is not free for jobs.
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max="max", memory__current=str(1 * GB))
    httpserver.expect_request("/v4/c1").respond_with_json({"DockerId": "engine"})
    httpserver.expect_request("/v4/c1/task").respond_with_json(
        {"Limits": {"Memory": 16384}},
    )
    httpserver.expect_request("/v4/c1/task/stats").respond_with_json(
        {
            "engine": {"memory_stats": {"usage": 1 * GB}},
            "sidecar": {
                "memory_stats": {"usage": 3 * GB, "stats": {"inactive_file": GB}},
            },
            "stopped": None,
        },
    )
    memory = layout.detect({ECS_METADATA_URI_ENV: httpserver.url_for("/v4/c1")})
    with _host_available(30 * GB):
        assert memory.available_mb() == 13 * 1024


def test_ecs_task_stats_failure_counts_no_other_usage(
    tmp_path: Path,
    httpserver: HTTPServer,
) -> None:
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max="max", memory__current=str(1 * GB))
    httpserver.expect_request("/v4/c1").respond_with_json({"DockerId": "engine"})
    httpserver.expect_request("/v4/c1/task").respond_with_json(
        {"Limits": {"Memory": 16384}},
    )
    httpserver.expect_request("/v4/c1/task/stats").respond_with_data("", status=500)
    memory = layout.detect({ECS_METADATA_URI_ENV: httpserver.url_for("/v4/c1")})
    with _host_available(30 * GB):
        assert memory.available_mb() == 15 * 1024


def test_ecs_task_stats_are_reused_between_reads(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/v4/c1").respond_with_json({"DockerId": "engine"})
    httpserver.expect_request("/v4/c1/task/stats").respond_with_json(
        {"sidecar": {"memory_stats": {"usage": 2 * GB}}},
    )
    stats = EcsTaskStats(httpserver.url_for("/v4/c1"))
    assert stats.other_containers_usage_bytes() == 2 * GB
    assert stats.other_containers_usage_bytes() == 2 * GB
    stats_requests = [r for r, _ in httpserver.log if r.path == "/v4/c1/task/stats"]
    assert len(stats_requests) == 1


# The kill switch


@pytest.mark.parametrize("value", ["host", " HOST "])
def test_host_mode_ignores_every_limit(tmp_path: Path, value: str) -> None:
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max=str(8 * GB), memory__current="0")
    memory = layout.detect({MEMORY_LIMIT_SOURCE_ENV: value})
    assert memory.limit_bytes is None
    with _host_available(30 * GB):
        assert memory.available_mb() == 30 * 1024


def test_unknown_mode_uses_the_container_limit(tmp_path: Path) -> None:
    layout = Layout(tmp_path, "0::/\n")
    layout.v2(memory__max=str(8 * GB), memory__current="0")
    assert layout.detect({MEMORY_LIMIT_SOURCE_ENV: "bogus"}).limit_bytes == 8 * GB
