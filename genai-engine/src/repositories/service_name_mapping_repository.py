import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db_models import (
    DatabaseServiceNameTaskMapping,
    DatabaseSpan,
    DatabaseTask,
    DatabaseTraceMetadata,
)
from repositories.resource_metadata_repository import ResourceMetadataRepository
from utils.task_utils import get_system_task_id

logger = logging.getLogger(__name__)


class ServiceNameMappingRepository:
    """Repository for managing service.name to task_id mappings.

    Handles CRUD operations for service name mappings and retroactive
    updates of traces when mappings are created or modified.
    """

    def __init__(
        self,
        db_session: Session,
        resource_metadata_repo: Optional[ResourceMetadataRepository] = None,
    ):
        self.db_session = db_session
        self.resource_metadata_repo = (
            resource_metadata_repo or ResourceMetadataRepository(db_session)
        )

    def create_mapping(
        self,
        service_name: str,
        task_id: str,
    ) -> tuple[DatabaseServiceNameTaskMapping, int]:
        """Create a service.name → task_id mapping and retroactively update traces.

        Args:
            service_name: The service name to map
            task_id: The task ID to map to

        Returns:
            tuple: (mapping, traces_updated_count)

        Raises:
            HTTPException: 404 if task not found, 409 if mapping already exists
        """
        # Validate task exists
        task = (
            self.db_session.query(DatabaseTask)
            .filter(DatabaseTask.id == task_id)
            .filter(DatabaseTask.archived == False)
            .first()
        )
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found or is archived",
            )

        # Check if mapping already exists
        existing = self.get_mapping(service_name)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Mapping for service.name '{service_name}' already exists (task_id: {existing.task_id})",
            )

        # Create mapping
        mapping = DatabaseServiceNameTaskMapping(
            service_name=service_name,
            task_id=task_id,
        )
        self.db_session.add(mapping)

        # Retroactively update traces currently assigned to system task
        traces_updated = self._retroactive_update_traces(service_name, task_id)

        self.db_session.commit()

        logger.info(
            f"Created service.name mapping: {service_name} → {task_id}, "
            f"updated {traces_updated} traces"
        )

        return mapping, traces_updated

    def _retroactive_update_traces(self, service_name: str, task_id: str) -> int:
        """Retroactively update traces from system task to the mapped task_id.

        Args:
            service_name: The service name
            task_id: The task ID to assign

        Returns:
            int: Number of traces updated
        """
        # Get system task ID
        system_task_id = get_system_task_id(self.db_session)

        # Get all resource_ids with this service.name
        resource_ids = self.resource_metadata_repo.get_resource_ids_by_service_name(
            service_name
        )

        if not resource_ids:
            logger.debug(f"No resources found with service.name={service_name}")
            return 0

        # Get all trace_ids currently assigned to system task with these resources
        trace_ids_query = (
            select(DatabaseTraceMetadata.trace_id)
            .where(DatabaseTraceMetadata.root_span_resource_id.in_(resource_ids))
            .where(DatabaseTraceMetadata.task_id == system_task_id)
        )
        trace_ids = [
            row[0] for row in self.db_session.execute(trace_ids_query).fetchall()
        ]

        if not trace_ids:
            logger.debug(
                f"No system task traces found with service.name={service_name}"
            )
            return 0

        # Update trace_metadata.task_id from system task to new task
        self.db_session.execute(
            update(DatabaseTraceMetadata)
            .where(DatabaseTraceMetadata.trace_id.in_(trace_ids))
            .values(task_id=task_id)
        )

        # Update database_span.task_id for all spans in these traces
        self.db_session.execute(
            update(DatabaseSpan)
            .where(DatabaseSpan.trace_id.in_(trace_ids))
            .values(task_id=task_id)
        )

        logger.info(
            f"Retroactively updated {len(trace_ids)} traces with service.name={service_name} from system task to task_id={task_id}"
        )

        return len(trace_ids)

    def get_mapping(
        self, service_name: str
    ) -> Optional[DatabaseServiceNameTaskMapping]:
        """Retrieve mapping for a service.name.

        Args:
            service_name: The service name to look up

        Returns:
            DatabaseServiceNameTaskMapping if found, None otherwise
        """
        return (
            self.db_session.query(DatabaseServiceNameTaskMapping)
            .filter(DatabaseServiceNameTaskMapping.service_name == service_name)
            .first()
        )

    def list_mappings(
        self,
        page: int = 0,
        page_size: int = 20,
    ) -> tuple[list[DatabaseServiceNameTaskMapping], int]:
        """List all service.name mappings with pagination.

        Args:
            page: Page number (0-indexed)
            page_size: Number of results per page

        Returns:
            tuple: (list of mappings, total count)
        """
        query = self.db_session.query(DatabaseServiceNameTaskMapping).order_by(
            DatabaseServiceNameTaskMapping.created_at.desc()
        )

        total_count = query.count()
        results = query.limit(page_size).offset(page * page_size).all()

        return results, total_count

    def update_mapping(
        self,
        service_name: str,
        new_task_id: str,
    ) -> tuple[DatabaseServiceNameTaskMapping, int]:
        """Update task_id for an existing mapping and retroactively reassign traces.

        Args:
            service_name: The service name
            new_task_id: The new task ID to map to

        Returns:
            tuple: (updated mapping, traces_updated_count)

        Raises:
            HTTPException: 404 if mapping or task not found
        """
        # Get existing mapping
        mapping = self.get_mapping(service_name)
        if not mapping:
            raise HTTPException(
                status_code=404,
                detail=f"Mapping for service.name '{service_name}' not found",
            )

        # Validate new task exists
        new_task = (
            self.db_session.query(DatabaseTask)
            .filter(DatabaseTask.id == new_task_id)
            .filter(DatabaseTask.archived == False)
            .first()
        )
        if not new_task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {new_task_id} not found or is archived",
            )

        old_task_id = mapping.task_id

        # Update mapping
        mapping.task_id = new_task_id

        # Retroactively reassign traces from old task to new task
        traces_updated = self._reassign_traces(service_name, old_task_id, new_task_id)

        self.db_session.commit()

        logger.info(
            f"Updated service.name mapping: {service_name} from {old_task_id} → {new_task_id}, "
            f"reassigned {traces_updated} traces"
        )

        return mapping, traces_updated

    def _reassign_traces(
        self, service_name: str, old_task_id: str, new_task_id: str
    ) -> int:
        """Reassign traces from old task to new task.

        Args:
            service_name: The service name
            old_task_id: The old task ID
            new_task_id: The new task ID

        Returns:
            int: Number of traces reassigned
        """
        # Get all resource_ids with this service.name
        resource_ids = self.resource_metadata_repo.get_resource_ids_by_service_name(
            service_name
        )

        if not resource_ids:
            return 0

        # Get all trace_ids with old task_id referencing these resources
        trace_ids_query = (
            select(DatabaseTraceMetadata.trace_id)
            .where(DatabaseTraceMetadata.root_span_resource_id.in_(resource_ids))
            .where(DatabaseTraceMetadata.task_id == old_task_id)
        )
        trace_ids = [
            row[0] for row in self.db_session.execute(trace_ids_query).fetchall()
        ]

        if not trace_ids:
            return 0

        # Update trace_metadata
        self.db_session.execute(
            update(DatabaseTraceMetadata)
            .where(DatabaseTraceMetadata.trace_id.in_(trace_ids))
            .values(task_id=new_task_id)
        )

        # Update spans
        self.db_session.execute(
            update(DatabaseSpan)
            .where(DatabaseSpan.trace_id.in_(trace_ids))
            .values(task_id=new_task_id)
        )

        return len(trace_ids)

    def delete_mapping(self, service_name: str) -> None:
        """Delete a service.name mapping.

        NOTE: This does NOT retroactively unassign traces. Traces that were
        already assigned via this mapping will keep their task_id assignments.

        Args:
            service_name: The service name

        Raises:
            HTTPException: 404 if mapping not found
        """
        mapping = self.get_mapping(service_name)
        if not mapping:
            raise HTTPException(
                status_code=404,
                detail=f"Mapping for service.name '{service_name}' not found",
            )

        self.db_session.delete(mapping)
        self.db_session.commit()

        logger.info(
            f"Deleted service.name mapping: {service_name} (traces keep their assignments)"
        )
