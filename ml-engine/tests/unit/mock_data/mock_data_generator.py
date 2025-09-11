import json
import os
import pathlib
from datetime import datetime, timezone
from uuid import uuid4

from arthur_client.api_bindings import *
from arthur_common.models.enums import ModelProblemType


def get_data_file(filename: str):
    return open(os.path.join(pathlib.Path(__file__).parent, filename))


def random_dataplane_user() -> User:
    return User(
        id=str(uuid4()),
        first_name="dp-name",
        last_name=None,
        user_type=UserType.DATA_PLANE,
        organization_name="",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        organization_id="",
        data_plane_id=str(uuid4()),
    )


def oidc_config(base_url: str) -> str:
    config = get_data_file("sample_oidc_config.json").read()
    config = config.replace("http://localhost:8080", base_url)
    return config


def random_job_job_run(data_plane_id: str | None = None) -> tuple[Job, JobRun]:
    job_id, job_run_id = str(uuid4()), str(uuid4())
    job_run = JobRun(
        job_id=job_id,
        id=job_run_id,
        state=JobState.RUNNING,
        job_attempt=0,
        start_timestamp=datetime.now(),
        end_timestamp=None,
    )
    job = Job(
        id=job_id,
        memory_requirements_mb=40,
        state=JobState.RUNNING,
        trigger_type=JobTrigger.USER,
        job_spec=JobSpec(
            ConnectorCheckJobSpec(
                connector_id="test_connector_id",
                connection_id="test_connection_id",
            ),
        ),
        kind=JobKind.CONNECTOR_CHECK,
        project_id=str(uuid4()),
        data_plane_id=data_plane_id if data_plane_id else str(uuid4()),
        queued_at=datetime.now(),
        ready_at=datetime.now(),
        attempts=0,
        max_attempts=0,
        job_priority=JobPriority.NUMBER_400,
    )
    return job, job_run


def random_model() -> Model:
    dataset_id = str(uuid4())
    return Model(
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        id="test_model_id",
        project_id="",
        name="yeet",
        description="",
        metric_config=ModelMetricSpec(aggregation_specs=[], id=""),
        schedule=ModelMetricsSchedule(
            id="test_schedule_id",
            cron="0 * * * *",
            lookback_period_seconds=3600,
        ),
        model_problem_types=[ModelProblemType.BINARY_CLASSIFICATION],
        datasets=[
            DatasetReference(
                dataset_id=dataset_id,
                dataset_name="test name",
                dataset_connector_type=ConnectorType.S3,
            ),
        ],
        data_plane_id=str(uuid4()),
    )


def random_access_token() -> str:
    return json.dumps(
        {
            "expires_in": 90000,
            "access_token": "123",
            "token_type": "type",
            "id_token": "123",
        },
    )
