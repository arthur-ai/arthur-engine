from typing import List, Optional
from uuid import UUID

from arthur_client.api_bindings import (
    PoliciesV1Api,
    PolicyAssignmentJobChainPatch,
)

_PAGE_SIZE = 100


def stamp_chain_job_id(
    policies_client: PoliciesV1Api,
    model_id: str,
    explicit_assignment_id: Optional[UUID],
    patch: PolicyAssignmentJobChainPatch,
) -> None:
    """Stamp a downstream chain job ID onto the relevant assignment(s).

    When the chain is scoped to a specific assignment (explicit_assignment_id
    set, e.g. POST /policy_assignments/{id}/check_compliance or
    /policies/{id}/check_compliance which fans out per-assignment at scope),
    stamp that one assignment.

    When the chain is model-wide (None — POST /models/{id}/check_compliance
    submits a single job for the whole model), fan out to every assignment
    on the model. The single downstream job will evaluate each assignment in
    turn, so the same spawned job ID legitimately applies to all of them.
    """
    if explicit_assignment_id is not None:
        target_ids = [str(explicit_assignment_id)]
    else:
        target_ids = _list_assignment_ids_for_model(policies_client, model_id)

    for aid in target_ids:
        policies_client.update_assignment_job_chain(
            assignment_id=aid,
            policy_assignment_job_chain_patch=patch,
        )


def _list_assignment_ids_for_model(
    policies_client: PoliciesV1Api,
    model_id: str,
) -> List[str]:
    ids: List[str] = []
    page = 1
    while True:
        resp = policies_client.list_model_policy_assignments(
            model_id=model_id,
            page=page,
            page_size=_PAGE_SIZE,
        )
        ids.extend(str(r.id) for r in resp.records)
        if len(resp.records) < _PAGE_SIZE:
            break
        page += 1
    return ids
