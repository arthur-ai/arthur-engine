import logging
from typing import Annotated

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db_session
from repositories.service_name_mapping_repository import ServiceNameMappingRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from schemas.request_schemas import (
    CreateServiceNameMappingRequest,
    UpdateServiceNameMappingRequest,
)
from schemas.response_schemas import (
    ServiceNameMappingCreateResponse,
    ServiceNameMappingListResponse,
    ServiceNameMappingResponse,
    ServiceNameMappingUpdateResponse,
)
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

logger = logging.getLogger(__name__)

service_name_mapping_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@service_name_mapping_routes.post(
    "/service_name_mappings",
    summary="Create Service Name Mapping",
    description="Create a service.name → task_id mapping and retroactively assign traces with this service.name (currently assigned to system task) to the specified task.",
    response_model=ServiceNameMappingCreateResponse,
    response_model_exclude_none=True,
    tags=["Service Name Mappings"],
    status_code=status.HTTP_201_CREATED,
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
def create_service_name_mapping(
    request: CreateServiceNameMappingRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ServiceNameMappingCreateResponse:
    """Create a service.name → task_id mapping and retroactively update traces."""
    try:
        repo = ServiceNameMappingRepository(db_session)

        # Create mapping and get retroactive update count
        mapping, traces_updated = repo.create_mapping(
            service_name=request.service_name,
            task_id=request.task_id,
        )

        # Get task name for response
        task_name = mapping.task.name if mapping.task else ""

        return ServiceNameMappingCreateResponse(
            service_name=mapping.service_name,
            task_id=mapping.task_id,
            task_name=task_name,
            created_at=mapping.created_at,
            traces_updated=traces_updated,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating service name mapping: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create service name mapping: {str(e)}",
        )
    finally:
        db_session.close()


@service_name_mapping_routes.get(
    "/service_name_mappings",
    summary="List Service Name Mappings",
    description="List all service.name → task_id mappings with pagination.",
    response_model=ServiceNameMappingListResponse,
    response_model_exclude_none=True,
    tags=["Service Name Mappings"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def list_service_name_mappings(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ServiceNameMappingListResponse:
    """List all service.name → task_id mappings with pagination."""
    try:
        repo = ServiceNameMappingRepository(db_session)

        mappings, total_count = repo.list_mappings(
            page=pagination_parameters.page,
            page_size=pagination_parameters.page_size,
        )

        # Convert to response format
        mapping_responses = [
            ServiceNameMappingResponse(
                service_name=m.service_name,
                task_id=m.task_id,
                task_name=m.task.name if m.task else "",
                created_at=m.created_at,
            )
            for m in mappings
        ]

        return ServiceNameMappingListResponse(
            mappings=mapping_responses,
            total_count=total_count,
        )
    except Exception as e:
        logger.error(f"Error listing service name mappings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list service name mappings: {str(e)}",
        )
    finally:
        db_session.close()


@service_name_mapping_routes.get(
    "/service_name_mappings/{service_name}",
    summary="Get Service Name Mapping",
    description="Get a specific service.name → task_id mapping.",
    response_model=ServiceNameMappingResponse,
    response_model_exclude_none=True,
    tags=["Service Name Mappings"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def get_service_name_mapping(
    service_name: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ServiceNameMappingResponse:
    """Get a specific service.name → task_id mapping."""
    try:
        repo = ServiceNameMappingRepository(db_session)
        mapping = repo.get_mapping(service_name)

        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mapping for service.name '{service_name}' not found",
            )

        return ServiceNameMappingResponse(
            service_name=mapping.service_name,
            task_id=mapping.task_id,
            task_name=mapping.task.name if mapping.task else "",
            created_at=mapping.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service name mapping: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service name mapping: {str(e)}",
        )
    finally:
        db_session.close()


@service_name_mapping_routes.put(
    "/service_name_mappings/{service_name}",
    summary="Update Service Name Mapping",
    description="Update task_id for an existing service.name mapping and retroactively reassign traces from old task to new task.",
    response_model=ServiceNameMappingUpdateResponse,
    response_model_exclude_none=True,
    tags=["Service Name Mappings"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
def update_service_name_mapping(
    service_name: str,
    request: UpdateServiceNameMappingRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ServiceNameMappingUpdateResponse:
    """Update task_id for an existing service.name mapping."""
    try:
        repo = ServiceNameMappingRepository(db_session)

        # Update mapping and get retroactive reassignment count
        mapping, traces_updated = repo.update_mapping(
            service_name=service_name,
            new_task_id=request.task_id,
        )

        # Get task name for response
        task_name = mapping.task.name if mapping.task else ""

        return ServiceNameMappingUpdateResponse(
            service_name=mapping.service_name,
            task_id=mapping.task_id,
            task_name=task_name,
            created_at=mapping.created_at,
            traces_updated=traces_updated,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service name mapping: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update service name mapping: {str(e)}",
        )
    finally:
        db_session.close()


@service_name_mapping_routes.delete(
    "/service_name_mappings/{service_name}",
    summary="Delete Service Name Mapping",
    description="Delete a service.name → task_id mapping. Note: This does NOT retroactively unassign traces that were already assigned via this mapping.",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Service Name Mappings"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
def delete_service_name_mapping(
    service_name: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> None:
    """Delete a service.name → task_id mapping."""
    try:
        repo = ServiceNameMappingRepository(db_session)
        repo.delete_mapping(service_name)

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting service name mapping: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete service name mapping: {str(e)}",
        )
    finally:
        db_session.close()
