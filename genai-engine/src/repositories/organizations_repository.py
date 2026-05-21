import uuid
from typing import Optional, overload

from sqlalchemy import Select
from sqlalchemy.orm import Session

from db_models import DatabaseOrganization


@overload
def lookup_org_id(
    session: Session, query: Select[tuple[uuid.UUID]]
) -> Optional[uuid.UUID]: ...
@overload
def lookup_org_id(
    session: Session, query: Select[tuple[uuid.UUID]], default: uuid.UUID
) -> uuid.UUID: ...


def lookup_org_id(
    session: Session,
    query: Select[tuple[uuid.UUID]],
    default: Optional[uuid.UUID] = None,
) -> Optional[uuid.UUID]:
    """Run a single-column `select(Task.org_id)` query and return the org id.

    Centralizes the "fetch the owning task's org_id, fall back to a default"
    pattern used by repositories that need to denormalize org_id onto new rows
    (e.g. feedback, agentic annotations, rule results). When a non-None
    `default` is supplied, the return type is non-Optional.
    """
    org_id = session.execute(query).scalar_one_or_none()
    return org_id if org_id is not None else default


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

    def create_organization(
        self,
        name: str,
        is_system: bool = False,
    ) -> DatabaseOrganization:
        db_org = DatabaseOrganization(name=name, is_system=is_system)
        self.db_session.add(db_org)
        # flush (not commit) so the caller controls the transaction boundary;
        # raises IntegrityError on the unique(name) constraint without aborting
        # any sibling work the caller has not yet committed.
        self.db_session.flush()
        return db_org
