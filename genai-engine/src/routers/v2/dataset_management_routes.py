from typing import Annotated, List, Optional
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.status import HTTP_204_NO_CONTENT

from dependencies import get_db_session, get_validated_agentic_task
from repositories.datasets_repository import DatasetRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Dataset, Task, User
from schemas.request_schemas import (
    DatasetUpdateRequest,
    NewDatasetRequest,
    NewDatasetVersionRequest,
)
from schemas.response_schemas import (
    DatasetResponse,
    DatasetVersionResponse,
    DatasetVersionRowResponse,
    ListDatasetVersionsResponse,
    SearchDatasetsResponse,
)
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

dataset_management_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)
datasets_router_tag = "Datasets"


###################################
#### Dataset Management Routes ####
###################################


@dataset_management_routes.post(
    "/tasks/{task_id}/datasets",
    description="Register a new dataset.",
    response_model=DatasetResponse,
    tags=[datasets_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
def create_dataset(
    request: NewDatasetRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
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
) -> DatasetResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        dataset_repo.update_dataset(dataset_id, request)
        dataset = dataset_repo.get_dataset(dataset_id)
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
) -> Response:
    try:
        dataset_repo = DatasetRepository(db_session)
        dataset_repo.delete_dataset(dataset_id)
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
    task: Task = Depends(get_validated_agentic_task),
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
) -> DatasetResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        return dataset_repo.get_dataset(dataset_id).to_response_model()
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
) -> DatasetVersionResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        dataset_repo.create_dataset_version(dataset_id, new_version_request)
        return dataset_repo.get_latest_dataset_version(dataset_id).to_response_model()
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
) -> ListDatasetVersionsResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        return dataset_repo.get_dataset_versions(
            dataset_id,
            latest_version_only,
            pagination_parameters,
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
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> DatasetVersionResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        return dataset_repo.get_dataset_version(
            dataset_id,
            version_number,
            pagination_parameters,
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
) -> DatasetVersionRowResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        db_row = dataset_repo.get_dataset_version_row(
            dataset_id,
            version_number,
            row_id,
        )

        # Convert database row to response format
        row_data = [
            {"column_name": key, "column_value": value}
            for key, value in db_row.data.items()
        ]

        return DatasetVersionRowResponse(
            id=db_row.id,
            data=row_data,
            created_at=int(db_row.created_at.timestamp() * 1000),
        )
    finally:
        db_session.close()
