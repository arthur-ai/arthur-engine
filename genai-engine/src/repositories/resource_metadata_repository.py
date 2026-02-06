import hashlib
import json
import logging
import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from db_models import DatabaseResourceMetadata

logger = logging.getLogger(__name__)


class ResourceMetadataRepository:
    """Repository for managing OpenTelemetry resource metadata.

    Handles creation, retrieval, and deduplication of resource metadata records
    that store resource attributes from OpenTelemetry traces.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_or_get_resource(
        self,
        resource_attributes: dict[str, Any],
        service_name: str | None,
    ) -> str:
        """Create or retrieve existing resource metadata record.

        Uses content-based hashing to deduplicate identical resource attributes.
        Multiple spans/traces with identical resource attributes will reference
        the same resource_id.

        Handles race conditions where multiple concurrent requests may try to
        create the same resource by using insert-then-query-on-conflict pattern.

        Args:
            resource_attributes: Dictionary of OpenTelemetry resource attributes
            service_name: Extracted service.name value (can be None)

        Returns:
            str: The resource_id (UUID) for the resource metadata record
        """
        # Generate deterministic ID based on resource attributes content
        resource_id = self._generate_resource_id(resource_attributes)

        # Check if resource already exists (common case - avoid insert attempt)
        existing = self.get_by_id(resource_id)
        if existing:
            logger.debug(
                f"Resource metadata already exists with id={resource_id}, "
                f"service_name={service_name}"
            )
            return resource_id

        # Try to create new resource
        try:
            resource = DatabaseResourceMetadata(
                id=resource_id,
                service_name=service_name,
                resource_attributes=resource_attributes,
            )
            self.db_session.add(resource)
            self.db_session.commit()

            logger.debug(
                f"Created resource metadata with id={resource_id}, "
                f"service_name={service_name}"
            )

            return resource_id

        except Exception as e:
            # Rollback failed insert
            self.db_session.rollback()

            # Handle race condition: another request created it between our check and insert
            # Query again to get the existing record
            existing = self.get_by_id(resource_id)
            if existing:
                logger.debug(
                    f"Resource metadata created by concurrent request with id={resource_id}, "
                    f"service_name={service_name}"
                )
                return resource_id

            # If still doesn't exist, this is a different error - re-raise
            logger.error(
                f"Failed to create resource metadata with id={resource_id}, "
                f"service_name={service_name}: {e}"
            )
            raise

    def _generate_resource_id(self, resource_attributes: dict[str, Any]) -> str:
        """Generate deterministic ID from resource attributes using SHA256 hash.

        Args:
            resource_attributes: Dictionary of resource attributes

        Returns:
            str: UUID v5 generated from hash of sorted resource attributes
        """
        # Sort keys for deterministic hashing
        sorted_attrs = json.dumps(resource_attributes, sort_keys=True)
        hash_digest = hashlib.sha256(sorted_attrs.encode("utf-8")).digest()

        # Convert first 16 bytes of hash to UUID
        # This ensures valid UUID format while maintaining determinism
        return str(uuid.UUID(bytes=hash_digest[:16]))

    def get_by_id(self, resource_id: str) -> Optional[DatabaseResourceMetadata]:
        """Retrieve resource metadata by ID.

        Args:
            resource_id: The resource ID

        Returns:
            DatabaseResourceMetadata if found, None otherwise
        """
        return (
            self.db_session.query(DatabaseResourceMetadata)
            .filter(DatabaseResourceMetadata.id == resource_id)
            .first()
        )

    def get_by_service_name(
        self,
        service_name: str,
        limit: int = 100,
    ) -> list[DatabaseResourceMetadata]:
        """Retrieve all resources with a specific service.name.

        Args:
            service_name: The service name to filter by
            limit: Maximum number of results to return

        Returns:
            List of DatabaseResourceMetadata records
        """
        return (
            self.db_session.query(DatabaseResourceMetadata)
            .filter(DatabaseResourceMetadata.service_name == service_name)
            .order_by(DatabaseResourceMetadata.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_resource_ids_by_service_name(self, service_name: str) -> list[str]:
        """Get all resource IDs for a specific service.name.

        Used for retroactive updates when creating service.name → task_id mappings.

        Args:
            service_name: The service name to filter by

        Returns:
            List of resource_ids
        """
        results = (
            self.db_session.query(DatabaseResourceMetadata.id)
            .filter(DatabaseResourceMetadata.service_name == service_name)
            .all()
        )
        return [row[0] for row in results]
