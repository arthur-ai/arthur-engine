"""How much memory the agent offers the Platform when it asks for the next job."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from arthur_client.api_bindings import User
from mock_data.mock_data_generator import random_job_job_run
from pytest_httpserver import HTTPServer

from job_agent import JobAgent, RunningJob
from memory_limits import MEMORY_LIMIT_SOURCE_ENV, ContainerMemory

MB = 1024 * 1024
GB = 1024 * MB


def _container(root: Path, limit: int, current: int) -> ContainerMemory:
    (root / "memory.max").write_text(f"{limit}\n")
    (root / "memory.current").write_text(f"{current}\n")
    return ContainerMemory.detect(root, {})


def _host_available(nbytes: int):
    return patch("memory_limits._host_available_bytes", return_value=nbytes)


def _agent(memory: ContainerMemory, host_bytes: int) -> JobAgent:
    with (
        _host_available(host_bytes),
        patch(
            "job_agent.ContainerMemory.detect",
            return_value=memory,
        ),
    ):
        return JobAgent()


def _running(memory_mb: int) -> RunningJob:
    return RunningJob(
        job_id="running",
        runner=MagicMock(),
        memory_requirements=memory_mb,
        job_run=MagicMock(),
    )


def test_budget_is_the_container_limit_not_the_host(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
    tmp_path: Path,
) -> None:
    # The dev incident: a 16 GB task on a VM reporting 30 GB free.
    agent = _agent(_container(tmp_path, 16 * GB, 1 * GB), 30 * GB)
    assert agent.total_memory_mb == 15 * 1024 - 400
    assert agent.host_total_memory_mb == 30 * 1024 - 400

    agent.running_jobs["running"] = _running(1500)
    with _host_available(30 * GB):
        assert agent._dequeue_memory_limit_mb() == 15 * 1024 - 400 - 1500


def test_real_time_usage_caps_the_offer_when_jobs_outgrow_their_requests(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
    tmp_path: Path,
) -> None:
    agent = _agent(_container(tmp_path, 16 * GB, 1 * GB), 30 * GB)
    agent.running_jobs["running"] = _running(1500)
    # The 1,500 MB job is now using 10 GB.
    (tmp_path / "memory.current").write_text(f"{11 * GB}\n")
    with _host_available(30 * GB):
        assert agent._dequeue_memory_limit_mb() == 5 * 1024


def test_an_idle_agent_still_offers_the_host_budget(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
    tmp_path: Path,
) -> None:
    # A 2 GB container cannot fit a 1,500 MB job beside the agent and the buffer.
    agent = _agent(_container(tmp_path, 2 * GB, 700 * MB), 8 * GB)
    assert agent.total_memory_mb < 1500
    with _host_available(8 * GB):
        assert agent._dequeue_memory_limit_mb() == 8 * 1024 - 400

        # Once the large job runs, nothing else is admitted beside it.
        agent.running_jobs["running"] = _running(1500)
        assert agent._dequeue_memory_limit_mb() == 0


def test_host_mode_offers_what_it_did_before(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
    tmp_path: Path,
) -> None:
    (tmp_path / "memory.max").write_text(f"{16 * GB}\n")
    memory = ContainerMemory.detect(tmp_path, {MEMORY_LIMIT_SOURCE_ENV: "host"})
    agent = _agent(memory, 30 * GB)
    assert agent.total_memory_mb == 30 * 1024 - 400
    agent.running_jobs["running"] = _running(1500)
    with _host_available(30 * GB):
        assert agent._dequeue_memory_limit_mb() == 30 * 1024 - 400 - 1500


def test_a_job_above_the_budget_is_logged(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    agent = _agent(_container(tmp_path, 2 * GB, 700 * MB), 8 * GB)
    job, job_run = random_job_job_run(test_data_plane_user.data_plane_id)
    job.memory_requirements_mb = 1500
    with (
        patch("job_agent.ProcessJobRunner") as runner,
        caplog.at_level(
            logging.WARNING,
        ),
    ):
        agent._start_job(job, job_run)
    runner.return_value.start.assert_called_once()
    assert "running it alone" in caplog.text
