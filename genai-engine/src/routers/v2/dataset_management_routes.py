from typing import Annotated, List, Optional
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.status import HTTP_204_NO_CONTENT

from dependencies import get_db_session
from repositories.datasets_repository import DatasetRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Dataset, DatasetTransform, User
from schemas.request_schemas import (
    DatasetTransformUpdateRequest,
    DatasetUpdateRequest,
    NewDatasetRequest,
    NewDatasetTransformRequest,
    NewDatasetVersionRequest,
)
from schemas.response_schemas import (
    DatasetResponse,
    DatasetTransformResponse,
    DatasetVersionResponse,
    ListDatasetTransformsResponse,
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
    "/datasets",
    description="Register a new dataset.",
    response_model=DatasetResponse,
    tags=[datasets_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
def create_dataset(
    request: NewDatasetRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> DatasetResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        dataset = Dataset._from_request_model(request)
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
    "/datasets/search",
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
) -> SearchDatasetsResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        datasets, count = dataset_repo.query_datasets(
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


###################################
#### Transform Management Routes ##
###################################


@dataset_management_routes.post(
    "/datasets/{dataset_id}/transforms",
    description="Create a new transform for a dataset.",
    response_model=DatasetTransformResponse,
    tags=[datasets_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
def create_transform(
    request: NewDatasetTransformRequest,
    dataset_id: UUID = Path(
        description="ID of the dataset to create the transform for.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> DatasetTransformResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        transform = DatasetTransform._from_request_model(dataset_id, request)
        dataset_repo.create_transform(transform)
        return transform.to_response_model()
    finally:
        db_session.close()


@dataset_management_routes.get(
    "/datasets/{dataset_id}/transforms",
    description="List all transforms for a dataset.",
    response_model=ListDatasetTransformsResponse,
    tags=[datasets_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_READ.value)
def list_transforms(
    dataset_id: UUID = Path(description="ID of the dataset to list transforms for."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ListDatasetTransformsResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        transforms = dataset_repo.list_transforms(dataset_id)
        return ListDatasetTransformsResponse(
            transforms=[transform.to_response_model() for transform in transforms],
        )
    finally:
        db_session.close()


@dataset_management_routes.get(
    "/datasets/{dataset_id}/transforms/{transform_id}",
    description="Get a specific transform.",
    response_model=DatasetTransformResponse,
    tags=[datasets_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_READ.value)
def get_transform(
    dataset_id: UUID = Path(description="ID of the dataset."),
    transform_id: UUID = Path(description="ID of the transform to fetch."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> DatasetTransformResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        return dataset_repo.get_transform(dataset_id, transform_id).to_response_model()
    finally:
        db_session.close()


@dataset_management_routes.put(
    "/datasets/{dataset_id}/transforms/{transform_id}",
    description="Update a transform.",
    response_model=DatasetTransformResponse,
    tags=[datasets_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
def update_transform(
    request: DatasetTransformUpdateRequest,
    dataset_id: UUID = Path(description="ID of the dataset."),
    transform_id: UUID = Path(description="ID of the transform to update."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> DatasetTransformResponse:
    try:
        dataset_repo = DatasetRepository(db_session)
        dataset_repo.update_transform(dataset_id, transform_id, request)
        transform = dataset_repo.get_transform(dataset_id, transform_id)
        return transform.to_response_model()
    finally:
        db_session.close()


@dataset_management_routes.delete(
    "/datasets/{dataset_id}/transforms/{transform_id}",
    description="Delete a transform.",
    tags=[datasets_router_tag],
    status_code=HTTP_204_NO_CONTENT,
)
@permission_checker(permissions=PermissionLevelsEnum.DATASET_WRITE.value)
def delete_transform(
    dataset_id: UUID = Path(description="ID of the dataset."),
    transform_id: UUID = Path(description="ID of the transform to delete."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    try:
        dataset_repo = DatasetRepository(db_session)
        dataset_repo.delete_transform(dataset_id, transform_id)
        return Response(status_code=HTTP_204_NO_CONTENT)
    finally:
        db_session.close()
