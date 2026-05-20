import uuid
from typing import Optional

from sqlalchemy.orm import Session

from db_models import DatabaseOrganization


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
