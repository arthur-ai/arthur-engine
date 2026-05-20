import uuid
from typing import Optional

from sqlalchemy.orm import Session

from db_models import DatabaseOrganization

# Well-known UUIDs for the seeded organizations. Mirrored in the
# `create_organizations_table` migration's seed INSERT and in the
# task / annotation backfills. Application code should reference these
# constants (not the names) — names may eventually be user-editable.
DEFAULT_ORG_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SYSTEM_ORG_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000002")


class OrganizationsRepository:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def get_organization_by_id(
        self,
        organization_id: uuid.UUID,
    ) -> Optional[DatabaseOrganization]:
        return (
            self.db_session.query(DatabaseOrganization)
            .filter(DatabaseOrganization.id == organization_id)
            .one_or_none()
        )
