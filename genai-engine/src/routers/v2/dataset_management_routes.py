from typing import Annotated, List, Optional, cast
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.status import HTTP_204_NO_CONTENT

from db_models.dataset_models import DatabaseDataset
from db_models.task_models import DatabaseTask
from dependencies import get_db_session, get_org_scope, get_validated_task
from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.datasets_repository import DatasetRepository
from repositories.metrics_repository import MetricRepository
from repositories.model_provider_repository import ModelProviderRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from repositories.trace_transform_repository import TraceTransformRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Dataset, Task, User
from schemas.request_schemas import (
    BulkAddTracesToDatasetRequest,
    DatasetUpdateRequest,
    NewDatasetRequest,
    NewDatasetVersionRequest,
    SyntheticDataConversationRequest,
    SyntheticDataGenerationRequest,
)
from schemas.response_schemas import (
    BulkAddTracesToDatasetResponse,
    DatasetResponse,
    DatasetVersionResponse,
    DatasetVersionRowColumnItemResponse,
    DatasetVersionRowResponse,
    ListDatasetVersionsResponse,
    SearchDatasetsResponse,
    SyntheticDataGenerationResponse,
    SyntheticDataPromptStatus,
)
from services.dataset_bulk_add_service import build_bulk_add_rows
from services.synthetic_data_service import SyntheticDataService
from utils.constants import (
    EMPTY_MODEL_NAME,
    EMPTY_MODEL_PROVIDER,
    MAX_BULK_ADD_TRACES,
    PRODUCTION_TAG,
    SYNTHETIC_DATA_SYSTEM_PROMPT_NAME,
    SYNTHETIC_DATASET_TASK_ID,
)
from utils.users import enforce_org_scope, permission_checker
from utils.utils import common_pagination_parameters

dataset_management_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)
datasets_router_tag = "Datasets"


###################################
#### Dataset Management Routes ####
###################################


def _dataset_org_id(db_session: Session, dataset_id: UUID) -> UUID:
    """Resolve the org that owns this dataset (via its parent task).

    Synthetic-data billing (UP-4390) must land on the dataset's org rather
    than the caller's scope so admin-driven runs still bill the right
    tenant.
    """
    org_id: Optional[UUID] = (
        db_session.query(DatabaseTask.org_id)
        .join(DatabaseDataset, DatabaseDataset.task_id == DatabaseTask.id)
        .filter(DatabaseDataset.id == dataset_id)
        .scalar()
    )
    if org_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset {dataset_id} not found.",
        )
    return org_id


@dataset_management_routes.post(
    "/tasks/{task_id}/datasets",
    description="Register a new dataset.",
    response_model=DatasetResponse,
    tags=[datasets_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
@enforce_org_scope()
def create_dataset(
    request: NewDatasetRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> DatasetResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        dataset = Dataset._from_request_model(task.id, request)
        dataset_repo.create_dataset(dataset)
        return dataset.to_response_model()
    finally:
        db_session.close()


@dataset_management_routes.patch(
    "/datasets/{dataset_id}",
    description="Update a dataset.",
    response_model=DatasetResponse,
    tags=[datasets_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
def update_dataset(
    request: DatasetUpdateRequest,
    dataset_id: UUID = Path(description="ID of the dataset to update."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> DatasetResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        dataset_repo.update_dataset(dataset_id, request, org_scope=org_scope)
        dataset = dataset_repo.get_dataset(dataset_id, org_scope=org_scope)
        return dataset.to_response_model()
    finally:
        db_session.close()


@dataset_management_routes.delete(
    "/datasets/{dataset_id}",
    description="Delete a dataset.",
    tags=[datasets_router_tag],
    status_code=HTTP_204_NO_CONTENT,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
def delete_dataset(
    dataset_id: UUID = Path(description="ID of the dataset to delete."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> Response:
    try:
        dataset_repo = DatasetRepository(db_session)
        dataset_repo.delete_dataset(dataset_id, org_scope=org_scope)
        return Response(status_code=HTTP_204_NO_CONTENT)
    finally:
        db_session.close()


@dataset_management_routes.get(
    "/tasks/{task_id}/datasets/search",
    description="Search datasets. Optionally can filter by dataset IDs and dataset name.",
    tags=[datasets_router_tag],
    response_model=SearchDatasetsResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_READ.value)
@enforce_org_scope()
def get_datasets(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    dataset_ids: Optional[List[UUID]] = Query(
        default=None,
        description="List of dataset ids to query for.",
    ),
    dataset_name: Optional[str] = Query(
        default=None,
        description="Dataset name substring to search for.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> SearchDatasetsResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        datasets, count = dataset_repo.query_datasets(
            task.id,
            pagination_parameters,
            dataset_ids,
            dataset_name,
        )
        return SearchDatasetsResponse(
            datasets=[dataset.to_response_model() for dataset in datasets],
            count=count,
        )
    finally:
        db_session.close()


@dataset_management_routes.get(
    "/datasets/{dataset_id}",
    description="Get a dataset.",
    tags=[datasets_router_tag],
    response_model=DatasetResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_READ.value)
def get_dataset(
    dataset_id: UUID = Path(description="ID of the dataset to fetch."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> DatasetResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        return dataset_repo.get_dataset(
            dataset_id, org_scope=org_scope
        ).to_response_model()
    finally:
        db_session.close()


@dataset_management_routes.post(
    "/datasets/{dataset_id}/versions",
    description="Create a new dataset version.",
    tags=[datasets_router_tag],
    response_model=DatasetVersionResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
def create_dataset_version(
    new_version_request: NewDatasetVersionRequest,
    dataset_id: UUID = Path(
        description="ID of the dataset to create a new version for.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> DatasetVersionResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        dataset_repo.create_dataset_version(
            dataset_id, new_version_request, org_scope=org_scope
        )
        return dataset_repo.get_latest_dataset_version(
            dataset_id, org_scope=org_scope
        ).to_response_model()
    finally:
        db_session.close()


@dataset_management_routes.post(
    "/datasets/{dataset_id}/bulk-add-traces",
    description="Bulk add traces to a dataset by running a transform against each trace "
    "and appending the extracted values as new rows in a single new dataset version.",
    tags=[datasets_router_tag],
    response_model=BulkAddTracesToDatasetResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
def bulk_add_traces_to_dataset(
    request: BulkAddTracesToDatasetRequest,
    dataset_id: UUID = Path(
        description="ID of the dataset to add traces to.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> BulkAddTracesToDatasetResponse:
    try:
        if len(request.trace_ids) > MAX_BULK_ADD_TRACES:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Cannot add more than {MAX_BULK_ADD_TRACES} traces in a single "
                    f"request; received {len(request.trace_ids)}."
                ),
            )

        # De-duplicate the incoming trace IDs preserving first-seen order so a
        # direct API caller passing duplicates doesn't get duplicate rows/results.
        # The cap is applied to the raw request list above, before de-duplication,
        # so 26 raw IDs still 422 even if some are duplicates.
        trace_ids = list(dict.fromkeys(request.trace_ids))

        if not trace_ids:
            return BulkAddTracesToDatasetResponse(
                success_count=0,
                total=0,
                results=[],
            )

        dataset_repo = DatasetRepository(db_session)

        # Validate the dataset exists and is owned by the caller up front so a
        # cross-org / non-existent dataset returns 404 (not a 200 with
        # success_count=0 when the transform produces no rows).
        dataset_repo.get_dataset(dataset_id, org_scope=org_scope)

        # Resolve the transform + its latest definition (404 if missing), mirroring
        # execute_trace_transform_extraction in the v1 transform routes.
        trace_transform_repo = TraceTransformRepository(db_session)
        trace_transform = trace_transform_repo.get_transform_by_id(
            request.transform_id,
            org_scope=org_scope,
        )
        if not trace_transform:
            raise HTTPException(
                status_code=404,
                detail=f"Transform {request.transform_id} not found",
            )

        versions = trace_transform_repo.list_versions(request.transform_id).versions
        if not versions:
            raise HTTPException(
                status_code=404,
                detail=f"No versions found for transform {request.transform_id}",
            )
        transform_definition = versions[0].definition

        # Resolve the dataset's column schema. When the dataset has no version yet
        # (empty schema), fall back to the transform definition's variable names so
        # that "extract -> row" still produces meaningful columns. Ownership was
        # already validated above, so the only 404 expected here is the genuine
        # "dataset has no version yet" case; anything else propagates.
        try:
            columns = dataset_repo.get_latest_dataset_version(
                dataset_id,
                org_scope=org_scope,
            ).column_names
        except HTTPException as e:
            if e.status_code != 404:
                raise
            columns = []
        if not columns:
            columns = [var.variable_name for var in transform_definition.variables]

        # Build the span repository once, then run the transform against each trace.
        tasks_metrics_repo = TasksMetricsRepository(db_session)
        metrics_repo = MetricRepository(db_session)
        span_repo = SpanRepository(db_session, tasks_metrics_repo, metrics_repo)

        rows, results = build_bulk_add_rows(
            span_repo=span_repo,
            columns=columns,
            transform_definition=transform_definition,
            trace_ids=trace_ids,
            org_scope=org_scope,
        )

        # Persist all successful rows in a single new dataset version.
        if rows:
            dataset_repo.create_dataset_version(
                dataset_id,
                NewDatasetVersionRequest(
                    rows_to_add=rows,
                    rows_to_delete=[],
                    rows_to_update=[],
                ),
                org_scope=org_scope,
            )

        return BulkAddTracesToDatasetResponse(
            success_count=len(rows),
            total=len(trace_ids),
            results=results,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@dataset_management_routes.get(
    "/datasets/{dataset_id}/versions",
    description="List dataset versions.",
    tags=[datasets_router_tag],
    response_model=ListDatasetVersionsResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_READ.value)
def get_dataset_versions(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    dataset_id: UUID = Path(
        description="ID of the dataset to fetch versions for.",
    ),
    latest_version_only: bool = Query(
        default=False,
        description="Whether to only include the latest version for the dataset in the response. Defaults to False.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> ListDatasetVersionsResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        return dataset_repo.get_dataset_versions(
            dataset_id,
            latest_version_only,
            pagination_parameters,
            org_scope=org_scope,
        ).to_response_model()
    finally:
        db_session.close()


@dataset_management_routes.get(
    "/datasets/{dataset_id}/versions/{version_number}",
    description="Fetch a dataset version.",
    tags=[datasets_router_tag],
    response_model=DatasetVersionResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_READ.value)
def get_dataset_version(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    dataset_id: UUID = Path(
        description="ID of the dataset to fetch the version for.",
    ),
    version_number: int = Path(description="Version number to fetch."),
    search: Optional[str] = Query(
        None,
        description="Search query to filter rows. Performs case-insensitive search across all column values.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> DatasetVersionResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        return dataset_repo.get_dataset_version(
            dataset_id,
            version_number,
            pagination_parameters,
            search_query=search,
            org_scope=org_scope,
        ).to_response_model()
    finally:
        db_session.close()


@dataset_management_routes.get(
    "/datasets/{dataset_id}/versions/{version_number}/rows/{row_id}",
    description="Fetch a specific row from a dataset version by row ID.",
    tags=[datasets_router_tag],
    response_model=DatasetVersionRowResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_READ.value)
def get_dataset_version_row(
    dataset_id: UUID = Path(
        description="ID of the dataset.",
    ),
    version_number: int = Path(description="Version number of the dataset."),
    row_id: UUID = Path(description="ID of the row to fetch."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> DatasetVersionRowResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        db_row = dataset_repo.get_dataset_version_row(
            dataset_id,
            version_number,
            row_id,
            org_scope=org_scope,
        )

        # Convert database row to response format
        row_data = [
            DatasetVersionRowColumnItemResponse(column_name=key, column_value=value)
            for key, value in db_row.data.items()
        ]

        return DatasetVersionRowResponse(
            id=db_row.id,
            data=row_data,
            created_at=int(db_row.created_at.timestamp() * 1000),
        )
    finally:
        db_session.close()


###########################################
#### Synthetic Data Generation Routes ####
###########################################


@dataset_management_routes.get(
    "/datasets/synthetic-data/prompt-status",
    summary="Get the model configuration stored in the SDG system prompt.",
    tags=[datasets_router_tag],
    response_model=SyntheticDataPromptStatus,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_READ.value)
def get_synthetic_data_prompt_status(
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> SyntheticDataPromptStatus:
    prompt_repo = AgenticPromptRepository(db_session)
    try:
        prompt = cast(
            AgenticPrompt,
            prompt_repo.get_llm_item_by_tag(
                task_id=SYNTHETIC_DATASET_TASK_ID,
                item_name=SYNTHETIC_DATA_SYSTEM_PROMPT_NAME,
                tag=PRODUCTION_TAG,
            ),
        )
    except ValueError:
        # Not bootstrapped yet
        return SyntheticDataPromptStatus.model_validate(
            {
                "model_provider": EMPTY_MODEL_PROVIDER,
                "model_name": EMPTY_MODEL_NAME,
                "is_placeholder": True,
            }
        )

    is_placeholder = (
        prompt.model_provider == EMPTY_MODEL_PROVIDER
        or prompt.model_name == EMPTY_MODEL_NAME
    )
    # Pydantic coerces the string sentinel ("empty") or enum value back into the
    # Union[ModelProvider, Literal["empty"]] at construction time.
    return SyntheticDataPromptStatus.model_validate(
        {
            "model_provider": prompt.model_provider,
            "model_name": prompt.model_name,
            "is_placeholder": is_placeholder,
        }
    )


@dataset_management_routes.post(
    "/datasets/{dataset_id}/versions/{version_number}/generate-synthetic",
    description="Generate synthetic data rows based on existing dataset patterns.",
    tags=[datasets_router_tag],
    response_model=SyntheticDataGenerationResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
def generate_synthetic_data(
    request: SyntheticDataGenerationRequest,
    dataset_id: UUID = Path(description="ID of the dataset."),
    version_number: int = Path(description="Version number of the dataset."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> SyntheticDataGenerationResponse:
    """
    Generate initial synthetic data rows based on the dataset configuration.

    The dataset must have at least 1 existing row to provide reference
    examples for the LLM.
    """
    dataset_repo = DatasetRepository(db_session)
    model_provider_repo = ModelProviderRepository(db_session)

    # Get the dataset version with pagination to get rows
    pagination = PaginationParameters(page=0, page_size=10)
    dataset_version = dataset_repo.get_dataset_version(
        dataset_id,
        version_number,
        pagination,
        org_scope=org_scope,
    )

    # Check that dataset has at least 1 row
    if dataset_version.total_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Dataset must have at least 1 row to generate synthetic data. "
            "Add some example rows first to provide reference patterns.",
        )

    # Get column names from the dataset version
    column_names = dataset_version.column_names

    # Convert existing rows to dict format for the service
    existing_rows = [
        {
            "data": [
                {"column_name": col.column_name, "column_value": col.column_value}
                for col in row.data
            ],
        }
        for row in dataset_version.rows
    ]

    # Create the synthetic data service and generate data
    synthetic_service = SyntheticDataService(model_provider_repo, db_session)
    org_id = _dataset_org_id(db_session, dataset_id)
    return synthetic_service.generate_initial(
        request=request,
        existing_rows=existing_rows,
        column_names=column_names,
        session_id=f"dataset:{dataset_id}:v{version_number}",
        org_id=org_id,
    )


@dataset_management_routes.post(
    "/datasets/{dataset_id}/versions/{version_number}/generate-synthetic/message",
    description="Send a message to refine synthetic data generation.",
    tags=[datasets_router_tag],
    response_model=SyntheticDataGenerationResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
def send_synthetic_data_message(
    request: SyntheticDataConversationRequest,
    dataset_id: UUID = Path(description="ID of the dataset."),
    version_number: int = Path(description="Version number of the dataset."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> SyntheticDataGenerationResponse:
    """
    Send a message to refine the synthetic data generation.

    This endpoint continues a conversation with the LLM to modify,
    add, or remove generated rows based on user instructions.
    The current state of the generated data (including any manual edits)
    is sent with each message.
    """
    dataset_repo = DatasetRepository(db_session)
    model_provider_repo = ModelProviderRepository(db_session)

    # Get the dataset version with pagination to get sample rows
    pagination = PaginationParameters(page=0, page_size=10)
    dataset_version = dataset_repo.get_dataset_version(
        dataset_id,
        version_number,
        pagination,
        org_scope=org_scope,
    )

    # Get column names from the dataset version
    column_names = dataset_version.column_names

    # Convert existing rows to dict format for the service
    existing_rows = [
        {
            "data": [
                {"column_name": col.column_name, "column_value": col.column_value}
                for col in row.data
            ],
        }
        for row in dataset_version.rows
    ]

    # Create the synthetic data service and continue conversation
    synthetic_service = SyntheticDataService(model_provider_repo, db_session)
    org_id = _dataset_org_id(db_session, dataset_id)
    return synthetic_service.continue_conversation(
        request=request,
        existing_rows=existing_rows,
        column_names=column_names,
        session_id=f"dataset:{dataset_id}:v{version_number}",
        org_id=org_id,
    )
