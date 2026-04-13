from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
from arthur_client.api_bindings import (
    CompliancePolicyCheckJobSpec,
    Job,
    JobKind,
    JobsV1Api,
    Model,
    ModelsV1Api,
    PatchJob,
    PoliciesV1Api,
    PostJob,
    PostJobBatch,
    PostJobKind,
    ScheduleComplianceJobsJobSpec,
)
from arthur_client.api_bindings.exceptions import NotFoundException
from arthur_common.tools.functions import hash_nonce

from job_executors.schedule_compliance_jobs_executor import (
    COMPLIANCE_CHECK_INTERVAL,
    ScheduleComplianceJobsExecutor,
    generate_next_compliance_job_series,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MODEL_ID = "test_model_id"
PROJECT_ID = "test_project_id"
SCHEDULE_ID = "test_schedule_id"
NONCE = "test_nonce"


def _make_mock_model(compliance_schedule_id: str = SCHEDULE_ID) -> Mock:
    model = Mock(spec=Model)
    model.id = MODEL_ID
    model.project_id = PROJECT_ID
    model.compliance_schedule_id = compliance_schedule_id
    return model


def _make_mock_job(
    schedule_id: str = SCHEDULE_ID,
    nonce: str = NONCE,
) -> Mock:
    job = Mock(spec=Job)
    job.id = "test_job_id"
    job.schedule_id = schedule_id
    job.nonce = nonce
    job.attempts = 1
    job.max_attempts = 3
    return job


def _make_mock_job_spec() -> Mock:
    job_spec = Mock(spec=ScheduleComplianceJobsJobSpec)
    job_spec.scope_model_id = MODEL_ID
    return job_spec


def _make_mock_assignments_response(total: int = 1) -> Mock:
    response = Mock()
    response.pagination = Mock()
    response.pagination.total_records = total
    return response


def _make_executor(
    models_client: Mock = None,
    jobs_client: Mock = None,
    policies_client: Mock = None,
) -> ScheduleComplianceJobsExecutor:
    return ScheduleComplianceJobsExecutor(
        models_client=models_client or Mock(spec=ModelsV1Api),
        jobs_client=jobs_client or Mock(spec=JobsV1Api),
        policies_client=policies_client or Mock(spec=PoliciesV1Api),
        logger=Mock(),
    )


# ---------------------------------------------------------------------------
# generate_next_compliance_job_series
# ---------------------------------------------------------------------------


class TestGenerateNextComplianceJobSeries:
    @patch(
        "job_executors.schedule_compliance_jobs_executor.datetime",
        wraps=datetime,
    )
    def test_generates_correct_number_of_jobs(self, mock_dt):
        now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        jobs = generate_next_compliance_job_series(
            model_id=MODEL_ID,
            nonce=NONCE,
            schedule_id=SCHEDULE_ID,
            k=3,
        )

        # k=3 compliance jobs + 1 self-chain = 4 total
        assert len(jobs) == 4

    @patch(
        "job_executors.schedule_compliance_jobs_executor.datetime",
        wraps=datetime,
    )
    def test_compliance_jobs_have_correct_kind_and_spec(self, mock_dt):
        now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        jobs = generate_next_compliance_job_series(
            model_id=MODEL_ID,
            nonce=NONCE,
            schedule_id=SCHEDULE_ID,
        )

        compliance_jobs = jobs[:-1]
        for job in compliance_jobs:
            assert job.kind == PostJobKind.COMPLIANCE_POLICY_CHECK
            spec = job.job_spec.actual_instance
            assert isinstance(spec, CompliancePolicyCheckJobSpec)
            assert spec.scope_model_id == MODEL_ID
            assert spec.policy_assignment_id is None
            assert job.schedule_id == SCHEDULE_ID

    @patch(
        "job_executors.schedule_compliance_jobs_executor.datetime",
        wraps=datetime,
    )
    def test_compliance_jobs_spaced_24h_apart(self, mock_dt):
        now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        jobs = generate_next_compliance_job_series(
            model_id=MODEL_ID,
            nonce=NONCE,
            schedule_id=SCHEDULE_ID,
        )

        compliance_jobs = jobs[:-1]
        for i, job in enumerate(compliance_jobs, start=1):
            expected_ready_at = now + COMPLIANCE_CHECK_INTERVAL * i
            assert job.ready_at == expected_ready_at

    @patch(
        "job_executors.schedule_compliance_jobs_executor.datetime",
        wraps=datetime,
    )
    def test_schedule_job_has_correct_properties(self, mock_dt):
        now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        jobs = generate_next_compliance_job_series(
            model_id=MODEL_ID,
            nonce=NONCE,
            schedule_id=SCHEDULE_ID,
            k=3,
        )

        schedule_job = jobs[-1]
        assert schedule_job.kind == PostJobKind.SCHEDULE_COMPLIANCE_JOBS
        spec = schedule_job.job_spec.actual_instance
        assert isinstance(spec, ScheduleComplianceJobsJobSpec)
        assert spec.scope_model_id == MODEL_ID
        assert schedule_job.nonce == hash_nonce(NONCE)
        assert schedule_job.schedule_id == SCHEDULE_ID
        # Self-chain ready_at matches last compliance job
        assert schedule_job.ready_at == now + COMPLIANCE_CHECK_INTERVAL * 3

    @patch(
        "job_executors.schedule_compliance_jobs_executor.datetime",
        wraps=datetime,
    )
    def test_custom_k_value(self, mock_dt):
        now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now

        jobs = generate_next_compliance_job_series(
            model_id=MODEL_ID,
            nonce=NONCE,
            schedule_id=SCHEDULE_ID,
            k=5,
        )

        assert len(jobs) == 6  # 5 compliance + 1 schedule
        assert jobs[-1].ready_at == now + COMPLIANCE_CHECK_INTERVAL * 5


# ---------------------------------------------------------------------------
# ScheduleComplianceJobsExecutor.execute
# ---------------------------------------------------------------------------


class TestScheduleComplianceJobsExecutor:
    def test_execute_happy_path(self):
        mock_models_client = Mock(spec=ModelsV1Api)
        mock_jobs_client = Mock(spec=JobsV1Api)
        mock_policies_client = Mock(spec=PoliciesV1Api)
        executor = _make_executor(mock_models_client, mock_jobs_client, mock_policies_client)

        mock_model = _make_mock_model()
        mock_models_client.get_model.return_value = mock_model

        # Model has assignments
        mock_policies_client.list_model_policy_assignments.return_value = (
            _make_mock_assignments_response(total=1)
        )

        # No existing jobs with same nonce
        mock_jobs_response = Mock()
        mock_jobs_response.records = []
        mock_jobs_client.get_jobs.return_value = mock_jobs_response

        job = _make_mock_job()
        job_spec = _make_mock_job_spec()

        executor.execute(job, job_spec)

        mock_models_client.get_model.assert_called_once_with(MODEL_ID)
        mock_jobs_client.post_submit_jobs_batch.assert_called_once()

        # Verify the batch contains 3 compliance jobs + 1 schedule job
        call_args = mock_jobs_client.post_submit_jobs_batch.call_args
        assert call_args.kwargs["project_id"] == PROJECT_ID
        batch = call_args.kwargs["post_job_batch"]
        assert isinstance(batch, PostJobBatch)
        assert len(batch.jobs) == 4

        compliance_jobs = [
            j for j in batch.jobs if j.kind == PostJobKind.COMPLIANCE_POLICY_CHECK
        ]
        schedule_jobs = [
            j for j in batch.jobs if j.kind == PostJobKind.SCHEDULE_COMPLIANCE_JOBS
        ]
        assert len(compliance_jobs) == 3
        assert len(schedule_jobs) == 1

    def test_execute_model_deleted_stops_retries(self):
        mock_models_client = Mock(spec=ModelsV1Api)
        mock_jobs_client = Mock(spec=JobsV1Api)
        executor = _make_executor(mock_models_client, mock_jobs_client)

        mock_models_client.get_model.side_effect = NotFoundException(
            status=404, reason="Not Found"
        )

        mock_updated_job = Mock(spec=Job)
        mock_updated_job.max_attempts = 1
        mock_jobs_client.update_job.return_value = mock_updated_job

        job = _make_mock_job()
        job_spec = _make_mock_job_spec()

        with pytest.raises(ValueError, match="no longer exists"):
            executor.execute(job, job_spec)

        mock_jobs_client.update_job.assert_called_once_with(
            job_id=job.id,
            patch_job=PatchJob(max_attempts=job.attempts),
        )
        mock_jobs_client.post_submit_jobs_batch.assert_not_called()

    def test_execute_missing_schedule_id_stops_retries(self):
        mock_models_client = Mock(spec=ModelsV1Api)
        mock_jobs_client = Mock(spec=JobsV1Api)
        executor = _make_executor(mock_models_client, mock_jobs_client)

        mock_models_client.get_model.return_value = _make_mock_model()

        mock_updated_job = Mock(spec=Job)
        mock_updated_job.max_attempts = 1
        mock_jobs_client.update_job.return_value = mock_updated_job

        job = _make_mock_job(schedule_id=None)
        job_spec = _make_mock_job_spec()

        with pytest.raises(ValueError, match="Schedule id must be defined"):
            executor.execute(job, job_spec)

        mock_jobs_client.update_job.assert_called_once()
        mock_jobs_client.post_submit_jobs_batch.assert_not_called()

    def test_execute_missing_nonce_stops_retries(self):
        mock_models_client = Mock(spec=ModelsV1Api)
        mock_jobs_client = Mock(spec=JobsV1Api)
        executor = _make_executor(mock_models_client, mock_jobs_client)

        mock_models_client.get_model.return_value = _make_mock_model()

        mock_updated_job = Mock(spec=Job)
        mock_updated_job.max_attempts = 1
        mock_jobs_client.update_job.return_value = mock_updated_job

        job = _make_mock_job(nonce=None)
        job_spec = _make_mock_job_spec()

        with pytest.raises(ValueError, match="Nonce expected"):
            executor.execute(job, job_spec)

        mock_jobs_client.update_job.assert_called_once()
        mock_jobs_client.post_submit_jobs_batch.assert_not_called()

    def test_execute_no_assignments_stops_chain(self):
        mock_models_client = Mock(spec=ModelsV1Api)
        mock_jobs_client = Mock(spec=JobsV1Api)
        mock_policies_client = Mock(spec=PoliciesV1Api)
        executor = _make_executor(mock_models_client, mock_jobs_client, mock_policies_client)

        mock_models_client.get_model.return_value = _make_mock_model()

        # Model has no assignments
        mock_policies_client.list_model_policy_assignments.return_value = (
            _make_mock_assignments_response(total=0)
        )

        mock_updated_job = Mock(spec=Job)
        mock_updated_job.max_attempts = 1
        mock_jobs_client.update_job.return_value = mock_updated_job

        job = _make_mock_job()
        job_spec = _make_mock_job_spec()

        with pytest.raises(ValueError, match="no policy assignments"):
            executor.execute(job, job_spec)

        mock_jobs_client.update_job.assert_called_once()
        mock_jobs_client.post_submit_jobs_batch.assert_not_called()

    def test_execute_mismatched_schedule_id_stops_chain(self):
        mock_models_client = Mock(spec=ModelsV1Api)
        mock_jobs_client = Mock(spec=JobsV1Api)
        executor = _make_executor(mock_models_client, mock_jobs_client)

        # Model has a different compliance_schedule_id than the job
        mock_models_client.get_model.return_value = _make_mock_model(
            compliance_schedule_id="other_schedule_id"
        )

        mock_updated_job = Mock(spec=Job)
        mock_updated_job.max_attempts = 1
        mock_jobs_client.update_job.return_value = mock_updated_job

        job = _make_mock_job()
        job_spec = _make_mock_job_spec()

        with pytest.raises(ValueError, match="orphaned"):
            executor.execute(job, job_spec)

        mock_jobs_client.update_job.assert_called_once()
        mock_jobs_client.post_submit_jobs_batch.assert_not_called()

    def test_execute_nonce_already_exists_stops_retries(self):
        mock_models_client = Mock(spec=ModelsV1Api)
        mock_jobs_client = Mock(spec=JobsV1Api)
        mock_policies_client = Mock(spec=PoliciesV1Api)
        executor = _make_executor(mock_models_client, mock_jobs_client, mock_policies_client)

        mock_model = _make_mock_model()
        mock_models_client.get_model.return_value = mock_model

        # Model has matching assignments
        mock_policies_client.list_model_policy_assignments.return_value = (
            _make_mock_assignments_response(total=1)
        )

        # Nonce already exists
        mock_jobs_response = Mock()
        mock_jobs_response.records = [Mock()]
        mock_jobs_client.get_jobs.return_value = mock_jobs_response

        mock_updated_job = Mock(spec=Job)
        mock_updated_job.max_attempts = 1
        mock_jobs_client.update_job.return_value = mock_updated_job

        job = _make_mock_job()
        job_spec = _make_mock_job_spec()

        with pytest.raises(ValueError, match="already exists"):
            executor.execute(job, job_spec)

        mock_jobs_client.get_jobs.assert_called_once_with(
            project_id=PROJECT_ID,
            nonce=hash_nonce(NONCE),
            page=1,
            page_size=1,
            kinds=[JobKind.SCHEDULE_COMPLIANCE_JOBS],
        )
        mock_jobs_client.update_job.assert_called_once()
        mock_jobs_client.post_submit_jobs_batch.assert_not_called()
