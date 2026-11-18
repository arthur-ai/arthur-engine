from typing import Optional

from pydantic import BaseModel, Field

from schemas.enums import ActorKind


class Actor(BaseModel):
    """The principal that created or changed a resource."""

    kind: ActorKind = Field(description="How the actor authenticated.")
    id: str = Field(
        description="Stable identifier: the identity provider subject for users, the "
        "API key id for API keys, 'master-key' for the admin key, and the named "
        "person for on-behalf-of requests.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Human-readable label: the user's email, the API key "
        "description, or the on-behalf-of person.",
    )


def created_by_columns(actor: Optional[Actor]) -> dict[str, Optional[str]]:
    """Column values for a HasCreatedBy row. All NULL when there is no actor."""
    return {
        "created_by_kind": actor.kind.value if actor else None,
        "created_by_id": actor.id if actor else None,
        "created_by_name": actor.name if actor else None,
    }


def actor_from_columns(
    kind: Optional[str],
    id: Optional[str],
    name: Optional[str],
) -> Optional[Actor]:
    """Rebuild the Actor stored on a HasCreatedBy row, or None when unrecorded."""
    if kind is None or id is None:
        return None
    return Actor(kind=ActorKind(kind), id=id, name=name)
