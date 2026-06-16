import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, overload

from fastapi import HTTPException
from sqlalchemy import Select, update
from sqlalchemy.orm import Session

from db_models import DatabaseOrganization
from dependencies import db_session_context

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrgTokenQuotaStatus:
    """Snapshot of an org's token-credit state at a moment in time."""

    tokens_limit: Optional[int]  # None = unlimited
    tokens_used: int

    @property
    def is_exhausted(self) -> bool:
        if self.tokens_limit is None:
            return False
        return self.tokens_used >= self.tokens_limit


TOKEN_LIMIT_EXCEEDED_ERROR_CODE = "TOKEN_LIMIT_EXCEEDED"
TOKEN_LIMIT_EXCEEDED_MESSAGE = (
    "Your organization has used all available LLM credits. "
    "Contact Arthur to purchase more."
)


def enforce_token_quota(db_session: Session, org_id: uuid.UUID) -> None:
    """Raise 402 if `org_id` has exhausted its lifetime token credit (UP-4390).

    Orgs with `tokens_limit IS NULL` are unmetered (default org, system org)
    and always pass. Callers route this in front of any LLM-triggering work:
    request-time via the route handler, background-job-start time via the
    worker.
    """
    status = OrganizationsRepository(db_session).get_token_quota_status(org_id)
    if status is None or not status.is_exhausted:
        return
    raise HTTPException(
        status_code=402,
        detail={
            "error_code": TOKEN_LIMIT_EXCEEDED_ERROR_CODE,
            "message": TOKEN_LIMIT_EXCEEDED_MESSAGE,
            "tokens_limit": status.tokens_limit,
            "tokens_used": status.tokens_used,
        },
    )


def record_org_token_usage(org_id: uuid.UUID, token_count: int) -> None:
    """Atomically bill an org for `token_count` tokens (UP-4390).

    Opens its own DB session so the write lands independently of the caller's
    transaction — the LLM API call already happened, so accounting must
    persist whether or not the surrounding request commits or rolls back.

    Non-positive token counts are a no-op (post-call accounting on an LLM
    response that didn't include usage must not subtract credits).
    """
    if token_count <= 0:
        return
    try:
        with db_session_context() as session:
            session.execute(
                update(DatabaseOrganization)
                .where(DatabaseOrganization.id == org_id)
                .values(
                    tokens_used=DatabaseOrganization.tokens_used + token_count,
                ),
            )
            session.commit()
    except Exception:
        # Never let a billing-write failure leak out as the user-facing
        # LLM error — log and move on.
        logger.exception("Failed to record token usage for org=%s", org_id)


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
        tokens_limit: Optional[int] = None,
        commit: bool = True,
    ) -> DatabaseOrganization:
        db_org = DatabaseOrganization(
            id=uuid.uuid4(),
            name=name,
            is_system=is_system,
            tokens_limit=tokens_limit,
            created_at=datetime.now(),
        )
        self.db_session.add(db_org)
        # With commit=False the caller controls the transaction; the flush
        # still surfaces the unique(name) IntegrityError so the caller can
        # retry without leaving a poisoned session.
        if commit:
            self.db_session.commit()
        else:
            self.db_session.flush()
        return db_org

    def get_token_quota_status(
        self,
        organization_id: uuid.UUID,
    ) -> Optional[OrgTokenQuotaStatus]:
        """Return current (tokens_limit, tokens_used). None if the org doesn't exist."""
        row = (
            self.db_session.query(
                DatabaseOrganization.tokens_limit,
                DatabaseOrganization.tokens_used,
            )
            .filter(DatabaseOrganization.id == organization_id)
            .one_or_none()
        )
        if row is None:
            return None
        return OrgTokenQuotaStatus(tokens_limit=row[0], tokens_used=row[1])
