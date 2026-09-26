import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from arthur_client.api_bindings import (
    ApiClient,
    ConnectorType,
    Dataset,
    DatasetConnector,
    DatasetLocator,
    DatasetLocatorField,
    DatasetReference,
    DatasetSchema,
    DatasetsV1Api,
    Model,
    ModelProblemType,
    ModelsV1Api,
    TaskConnectionInfo,
    TasksV1Api,
    TaskValidationAPIKey,
)
from arthur_client.api_bindings.exceptions import ApiException
from arthur_client.auth import (
    ArthurClientCredentialsAPISession,
    ArthurOAuthSessionAPIConfiguration,
    ArthurOIDCMetadata,
)
from arthur_common.models.connectors import SHIELD_DATASET_TASK_ID_FIELD
from arthur_common.models.response_schemas import TaskResponse
from mock_data.api_mock_helpers import (
    expect_delete_dataset,
    expect_post_connector_dataset,
    expect_post_model,
    expect_post_model_rejection,
    expect_put_task_connection_info,
)
from mock_data.mock_data_generator import random_model
from pytest_httpserver import HTTPServer

from config import Config
from job_executors.task_management_job_executors import (
    LEGACY_SINGLE_DATASET_FALLBACK_PROBLEM_TYPE,
    TaskManagementJobExecutor,
    _platform_rejection_detail,
    _TaskDatasetAndModelCreator,
)

# What a pre-consolidation platform answers a two-dataset shield model with.
SINGLE_DATASET_REJECTION_DETAIL = (
    "All Arthur shield models must be linked to exactly one dataset. When creating a "
    "model linked to a shield dataset, there cannot be additional datasets linked to "
    "the model."
)

CONNECTOR_ID = "0f0b7bb5-2e64-4b27-9b5c-4b4c6b8f0a11"
PROJECT_ID = "8b0e1e2c-3d4f-4a5b-8c7d-9e0f1a2b3c4d"
MODEL_ID = "test_model_id"


@pytest.fixture()
def api_client(app_plane_http_server: HTTPServer) -> ApiClient:
    """A real generated client pointed at the mock app plane."""
    session = ArthurClientCredentialsAPISession(
        client_id=Config.settings.ARTHUR_CLIENT_ID,
        client_secret=Config.settings.ARTHUR_CLIENT_SECRET,
        metadata=ArthurOIDCMetadata(
            arthur_host=Config.settings.ARTHUR_API_HOST,
            verify_ssl=False,
        ),
        verify=False,
    )
    return ApiClient(
        configuration=ArthurOAuthSessionAPIConfiguration(
            session=session,
            verify_ssl=False,
        ),
    )


def mock_shield_connector() -> Mock:
    conn = Mock()
    conn.connector_config.id = CONNECTOR_ID
    conn.connector_config.name = "test connector"
    conn.shield_external_host = "https://shield.test"
    conn.create_task_validation_key.return_value = Mock(
        id="validation_key_id",
        key="validation_key",
        description="Task Validation Key",
    )
    return conn


def task_response() -> TaskResponse:
    now = datetime.now(timezone.utc)
    return TaskResponse(
        id=str(uuid4()),
        name="test task",
        created_at=int(now.timestamp()),
        updated_at=int(now.timestamp()),
        rules=[],
    )


def dataset_response(dataset_id: str, task_id: str) -> Dataset:
    now = datetime.now(timezone.utc)
    return Dataset(
        created_at=now,
        updated_at=now,
        id=dataset_id,
        name=f"dataset {dataset_id}",
        dataset_locator=DatasetLocator(
            fields=[
                DatasetLocatorField(key=SHIELD_DATASET_TASK_ID_FIELD, value=task_id),
            ],
        ),
        dataset_schema=DatasetSchema(alias_mask={}, columns=[], column_names={}),
        data_plane_id=str(uuid4()),
        project_id=PROJECT_ID,
        model_problem_type=ModelProblemType.ARTHUR_SHIELD,
        connector=DatasetConnector(
            id=CONNECTOR_ID,
            name="test connector",
            connector_type=ConnectorType.SHIELD,
        ),
    )


def task_connection_info() -> TaskConnectionInfo:
    now = datetime.now(timezone.utc)
    return TaskConnectionInfo(
        created_at=now,
        updated_at=now,
        api_host="https://shield.test",
        validation_key=TaskValidationAPIKey(
            id="validation_key_id",
            name="Task Validation Key",
            key="validation_key",
        ),
    )


def stub_task_creation(
    app_plane_http_server: HTTPServer,
    task: TaskResponse,
    dataset_ids: list[str],
    reject_model_creates: int = 0,
) -> Model:
    """
    Stubs one dataset creation per id in dataset_ids, a delete for each of them, and
    a model creation preceded by reject_model_creates platform rejections.
    """
    for dataset_id in dataset_ids:
        expect_post_connector_dataset(
            app_plane_http_server,
            CONNECTOR_ID,
            dataset_response(dataset_id, task.id),
        )
        expect_delete_dataset(app_plane_http_server, dataset_id)

    for _ in range(reject_model_creates):
        expect_post_model_rejection(
            app_plane_http_server,
            PROJECT_ID,
            SINGLE_DATASET_REJECTION_DETAIL,
        )

    model = random_model()
    expect_post_model(app_plane_http_server, PROJECT_ID, model)
    expect_put_task_connection_info(
        app_plane_http_server,
        MODEL_ID,
        task_connection_info(),
    )
    return model


def build_creator(
    api_client: ApiClient,
    task: TaskResponse,
    legacy_task_type: str | None = None,
) -> _TaskDatasetAndModelCreator:
    return _TaskDatasetAndModelCreator(
        task=task,
        onboarding_identifier=None,
        conn=mock_shield_connector(),
        datasets_client=DatasetsV1Api(api_client),
        models_client=ModelsV1Api(api_client),
        tasks_client=TasksV1Api(api_client),
        logger=Mock(),
        legacy_task_type=legacy_task_type,
    )


def posted_dataset_bodies(server: HTTPServer) -> list[dict[str, Any]]:
    return [
        json.loads(request.get_data())
        for request, _ in server.log
        if request.method == "POST" and request.path.endswith("/datasets")
    ]


def posted_model_bodies(server: HTTPServer) -> list[dict[str, Any]]:
    return [
        json.loads(request.get_data())
        for request, _ in server.log
        if request.method == "POST" and request.path.endswith("/models")
    ]


def deleted_dataset_ids(server: HTTPServer) -> list[str]:
    return [
        request.path.rsplit("/", 1)[-1]
        for request, _ in server.log
        if request.method == "DELETE" and "/api/v1/datasets/" in request.path
    ]


@pytest.mark.parametrize(
    "body, expected",
    [
        (json.dumps({"detail": "  two   datasets  "}), "two datasets"),
        ("plain text, not json", "plain text, not json"),
        (json.dumps(["not", "a", "mapping"]), '["not", "a", "mapping"]'),
        (json.dumps({"no_detail_key": "x"}), '{"no_detail_key": "x"}'),
        (None, "no error message in the platform's response"),
        ("   ", "no error message in the platform's response"),
        (json.dumps({"detail": "x" * 600}), "x" * 500 + "..."),
    ],
    ids=[
        "detail_is_whitespace_normalized",
        "body_is_not_json",
        "body_is_not_a_mapping",
        "body_has_no_detail",
        "body_is_absent",
        "body_is_blank",
        "runaway_body_is_truncated",
    ],
)
def test_platform_rejection_detail_degrades_gracefully(
    body: str | None,
    expected: str,
):
    """
    The retry log line reads this, so an odd response body must not be what raises.
    """
    assert _platform_rejection_detail(ApiException(status=400, body=body)) == expected


def test_consolidated_platform_creates_both_datasets_on_the_first_attempt(
    app_plane_http_server: HTTPServer,
    api_client: ApiClient,
):
    """
    Against a platform that accepts the consolidated shape nothing changed when the
    version probe was removed: the same two dataset POSTs in the same order, then one
    model POST, with no rejected attempt and no rollback.
    """
    task = task_response()
    stub_task_creation(
        app_plane_http_server,
        task,
        dataset_ids=["traces_dataset", "guardrails_dataset"],
    )

    model, datasets = build_creator(api_client, task).create()

    assert model.id == MODEL_ID
    assert len(datasets) == 2

    dataset_bodies = posted_dataset_bodies(app_plane_http_server)
    assert [body["model_problem_type"] for body in dataset_bodies] == [
        ModelProblemType.AGENTIC_TRACE.value,
        ModelProblemType.ARTHUR_SHIELD.value,
    ]
    assert [body["name"] for body in dataset_bodies] == [
        f"{task.name} - traces",
        f"{task.name} - guardrails",
    ]

    model_bodies = posted_model_bodies(app_plane_http_server)
    assert len(model_bodies) == 1
    assert model_bodies[0]["dataset_ids"] == ["traces_dataset", "guardrails_dataset"]
    assert deleted_dataset_ids(app_plane_http_server) == []


@pytest.mark.parametrize(
    "legacy_task_type, expected_problem_type",
    [
        (None, LEGACY_SINGLE_DATASET_FALLBACK_PROBLEM_TYPE),
        ("traditional", ModelProblemType.ARTHUR_SHIELD),
        ("agentic", ModelProblemType.AGENTIC_TRACE),
    ],
)
def test_old_platform_creates_single_dataset(
    app_plane_http_server: HTTPServer,
    api_client: ApiClient,
    legacy_task_type: str | None,
    expected_problem_type: ModelProblemType,
):
    """
    Which dataset the fallback keeps: the create path reads it from the raw job
    spec's legacy task_type, and the link path, which has no such signal, lands on
    LEGACY_SINGLE_DATASET_FALLBACK_PROBLEM_TYPE.
    """
    task = task_response()
    stub_task_creation(
        app_plane_http_server,
        task,
        dataset_ids=["traces_dataset", "guardrails_dataset", "only_dataset"],
        reject_model_creates=1,
    )

    model, datasets = build_creator(
        api_client,
        task,
        legacy_task_type=legacy_task_type,
    ).create()

    assert model.id == MODEL_ID
    assert len(datasets) == 1

    dataset_bodies = posted_dataset_bodies(app_plane_http_server)
    assert dataset_bodies[-1]["model_problem_type"] == expected_problem_type.value
    # Pre-consolidation the single dataset was named after the task, no suffix.
    assert dataset_bodies[-1]["name"] == task.name

    model_bodies = posted_model_bodies(app_plane_http_server)
    assert len(model_bodies) == 2
    assert model_bodies[-1]["dataset_ids"] == ["only_dataset"]
    # The rejected two-dataset attempt left nothing behind.
    assert sorted(deleted_dataset_ids(app_plane_http_server)) == [
        "guardrails_dataset",
        "traces_dataset",
    ]


def test_pre_consolidation_rejection_falls_back_to_a_single_dataset(
    app_plane_http_server: HTTPServer,
    api_client: ApiClient,
):
    """
    The whole of the old-platform path: one rejected two-dataset attempt whose
    datasets are rolled back, the rejection logged with the platform's own words,
    then the legacy single-dataset shape.
    """
    task = task_response()
    stub_task_creation(
        app_plane_http_server,
        task,
        dataset_ids=["traces_dataset", "guardrails_dataset", "retry_dataset"],
        reject_model_creates=1,
    )

    creator = build_creator(api_client, task)
    model, datasets = creator.create()

    assert model.id == MODEL_ID
    assert len(datasets) == 1

    # The retry is logged with the platform's own reason, not just the fact of it.
    retry_logs = [
        call.args[0]
        for call in creator.logger.warning.call_args_list
        if "retrying with a single dataset" in call.args[0]
    ]
    assert len(retry_logs) == 1
    assert "HTTP 400" in retry_logs[0]
    assert SINGLE_DATASET_REJECTION_DETAIL in retry_logs[0]

    dataset_bodies = posted_dataset_bodies(app_plane_http_server)
    assert [body["model_problem_type"] for body in dataset_bodies] == [
        ModelProblemType.AGENTIC_TRACE.value,
        ModelProblemType.ARTHUR_SHIELD.value,
        LEGACY_SINGLE_DATASET_FALLBACK_PROBLEM_TYPE.value,
    ]

    assert [body["name"] for body in dataset_bodies] == [
        f"{task.name} - traces",
        f"{task.name} - guardrails",
        task.name,
    ]

    model_bodies = posted_model_bodies(app_plane_http_server)
    assert len(model_bodies) == 2
    assert model_bodies[0]["dataset_ids"] == ["traces_dataset", "guardrails_dataset"]
    assert model_bodies[1]["dataset_ids"] == ["retry_dataset"]

    # The rejected attempt's datasets are gone; the retry's is the one that is kept.
    assert sorted(deleted_dataset_ids(app_plane_http_server)) == [
        "guardrails_dataset",
        "traces_dataset",
    ]


def test_failed_retry_leaves_no_orphaned_datasets(
    app_plane_http_server: HTTPServer,
    api_client: ApiClient,
):
    task = task_response()
    # Both the two-dataset attempt and the single-dataset retry are rejected.
    stub_task_creation(
        app_plane_http_server,
        task,
        dataset_ids=["traces_dataset", "guardrails_dataset", "retry_dataset"],
        reject_model_creates=2,
    )

    with pytest.raises(ApiException) as exc_info:
        build_creator(api_client, task).create()

    assert exc_info.value.status == 400
    assert len(posted_dataset_bodies(app_plane_http_server)) == 3
    assert sorted(deleted_dataset_ids(app_plane_http_server)) == [
        "guardrails_dataset",
        "retry_dataset",
        "traces_dataset",
    ]


def test_unrelated_rejection_is_not_retried(
    app_plane_http_server: HTTPServer,
    api_client: ApiClient,
):
    task = task_response()
    for dataset_id in ("traces_dataset", "guardrails_dataset"):
        expect_post_connector_dataset(
            app_plane_http_server,
            CONNECTOR_ID,
            dataset_response(dataset_id, task.id),
        )
        expect_delete_dataset(app_plane_http_server, dataset_id)
    expect_post_model_rejection(
        app_plane_http_server,
        PROJECT_ID,
        "Onboarding identifier already in use.",
    )

    with pytest.raises(ApiException):
        build_creator(api_client, task).create()

    # A 400 that is not the one-dataset constraint must not trigger the fallback.
    assert len(posted_dataset_bodies(app_plane_http_server)) == 2
    assert len(posted_model_bodies(app_plane_http_server)) == 1


def test_task_dataset_lookup_tolerates_a_single_dataset(
    app_plane_http_server: HTTPServer,
    api_client: ApiClient,
):
    """A model an old platform accepted carries one dataset; task management must
    still find it."""
    task = task_response()
    dataset = dataset_response("only_dataset", task.id)
    app_plane_http_server.expect_request(
        f"/api/v1/datasets/{dataset.id}",
    ).respond_with_data(
        dataset.model_dump_json(),
        content_type="application/json",
    )
    model = random_model()
    model.datasets = [
        DatasetReference(
            dataset_id=dataset.id,
            dataset_name=str(dataset.name),
            dataset_connector_type=ConnectorType.SHIELD,
        ),
    ]

    executor = TaskManagementJobExecutor(
        models_client=ModelsV1Api(api_client),
        datasets_client=DatasetsV1Api(api_client),
        tasks_client=TasksV1Api(api_client),
        connector_constructor=Mock(),
        logger=Mock(),
    )

    assert [d.id for d in executor._lookup_models_task_datasets(model=model)] == [
        dataset.id,
    ]
