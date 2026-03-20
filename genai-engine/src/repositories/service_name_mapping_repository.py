import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_models import DatabaseServiceNameTaskMapping

logger = logging.getLogger(__name__)


class ServiceNameMappingRepository:
    """Repository for managing service name to task ID mappings.

    Handles creation, retrieval, and querying of immutable service name mappings.
    Mappings are never updated once created - they are permanent associations.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_task_id_by_service_name(self, service_name: str) -> Optional[str]:
        """Retrieve task_id for a given service name.

        Args:
            service_name: The service name to lookup

        Returns:
            str: The task_id if mapping exists, None otherwise
        """
        mapping = (
            self.db_session.query(DatabaseServiceNameTaskMapping)
            .filter(DatabaseServiceNameTaskMapping.service_name == service_name)
            .first()
        )
        return mapping.task_id if mapping else None

    def mapping_exists(self, service_name: str) -> bool:
        """Check if a mapping exists for a service name.

        Args:
            service_name: The service name to check

        Returns:
            bool: True if mapping exists, False otherwise
        """
        return (
            self.db_session.query(DatabaseServiceNameTaskMapping.service_name)
            .filter(DatabaseServiceNameTaskMapping.service_name == service_name)
            .first()
            is not None
        )

    def create_mapping(
        self,
        service_name: str,
        task_id: str,
    ) -> DatabaseServiceNameTaskMapping:
        """Create a new service name to task ID mapping.

        This method is idempotent and handles race conditions. If a mapping
        already exists (either created by this call or concurrently by another),
        the existing mapping is returned.

        Args:
            service_name: The service name
            task_id: The task ID to map to

        Returns:
            DatabaseServiceNameTaskMapping: The created or existing mapping

        Raises:
            IntegrityError: If task_id doesn't exist (foreign key constraint)
        """
        try:
            mapping = DatabaseServiceNameTaskMapping(
                service_name=service_name,
                task_id=task_id,
            )
            self.db_session.add(mapping)
            self.db_session.commit()

            logger.info(f"Created service name mapping: {service_name} → {task_id}")
            return mapping

        except IntegrityError as e:
            self.db_session.rollback()

            # Check if it's a duplicate key error (mapping already exists)
            existing = self.get_mapping(service_name)
            if existing:
                logger.debug(
                    f"Service name mapping already exists: {service_name} → {existing.task_id}"
                )
                return existing
            else:
                # It's a foreign key constraint failure (invalid task_id)
                logger.error(
                    f"Failed to create mapping for {service_name} → {task_id}: {e}"
                )
                raise

    def get_mapping(
        self,
        service_name: str,
    ) -> Optional[DatabaseServiceNameTaskMapping]:
        """Retrieve full mapping record for a service name.

        Args:
            service_name: The service name to lookup

        Returns:
            DatabaseServiceNameTaskMapping if found, None otherwise
        """
        return (
            self.db_session.query(DatabaseServiceNameTaskMapping)
            .filter(DatabaseServiceNameTaskMapping.service_name == service_name)
            .first()
        )

    def get_all_mappings(
        self,
        limit: int = 1000,
    ) -> list[DatabaseServiceNameTaskMapping]:
        """Retrieve all service name mappings.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of DatabaseServiceNameTaskMapping records
        """
        return (
            self.db_session.query(DatabaseServiceNameTaskMapping)
            .order_by(DatabaseServiceNameTaskMapping.created_at.desc())
            .limit(limit)
            .all()
        )

    def delete_mapping(self, service_name: str) -> bool:
        """Delete a service name mapping.

        WARNING: This is an admin operation. Deleting mappings can cause
        traces to be reassigned to different tasks if they arrive after deletion.

        Args:
            service_name: The service name mapping to delete

        Returns:
            bool: True if mapping was deleted, False if not found
        """
        mapping = self.get_mapping(service_name)
        if not mapping:
            return False

        self.db_session.delete(mapping)
        self.db_session.commit()

        logger.warning(f"Deleted service name mapping: {service_name}")
        return True

    def get_service_names_by_task_id(self, task_id: str) -> list[str]:
        """Get all service names mapped to a task_id (reverse lookup).

        Args:
            task_id: The task ID to look up

        Returns:
            List of service names mapped to this task (empty list if none)
        """
        mappings = (
            self.db_session.query(DatabaseServiceNameTaskMapping)
            .filter(DatabaseServiceNameTaskMapping.task_id == task_id)
            .all()
        )
        return [mapping.service_name for mapping in mappings]
