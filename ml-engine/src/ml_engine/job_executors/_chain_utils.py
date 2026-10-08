from typing import List, Literal, Optional
from uuid import UUID

from arthur_client.api_bindings import (
    PoliciesV1Api,
    PolicyAssignment,
    PolicyAssignmentJobChainPatch,
)

_PAGE_SIZE = 100

# The chain column the stamping job must occupy on an assignment for its stamp to
# belong there: a metrics job stamps the alert check, an alert check stamps the
# compliance check.
PreviousStage = Literal["metrics_calc_job", "alerts_check_job"]


def stamp_chain_job_id(
    policies_client: PoliciesV1Api,
    model_id: str,
    explicit_assignment_id: Optional[UUID],
    patch: PolicyAssignmentJobChainPatch,
    *,
    current_job_id: str,
    previous_stage: PreviousStage,
) -> None:
    """Stamp a downstream chain job ID onto the assignment(s) whose chain this
    job heads.

    When the chain is scoped to a specific assignment (explicit_assignment_id
    set, e.g. POST /policy_assignments/{id}/check_compliance or
    /policies/{id}/check_compliance which fans out per-assignment at scope),
    only that assignment is considered. When the chain is model-wide (None,
    as with POST /models/{id}/check_compliance or a scheduled metrics run),
    every assignment on the model is.

    Either way an assignment is stamped only if its `previous_stage` job is
    this job. The Platform reads the three chain columns as one chain, so a
    stamp from a job that is not the assignment's current chain would corrupt
    it: a scheduled metrics run spawns the same alert and compliance jobs
    without heading any assignment's chain, and a check the user restarted
    while this chain was still running has a new head.

    Both cases read the model's assignment listing, the one call the engine's
    permissions are known to cover, rather than fetching one assignment.
    """
    assignments = _list_assignments_for_model(policies_client, model_id)
    if explicit_assignment_id is not None:
        assignments = [
            assignment
            for assignment in assignments
            if str(assignment.id) == str(explicit_assignment_id)
        ]

    for assignment in assignments:
        previous_job = getattr(assignment, previous_stage)
        if previous_job is None or str(previous_job.id) != str(current_job_id):
            continue
        policies_client.update_assignment_job_chain(
            assignment_id=str(assignment.id),
            policy_assignment_job_chain_patch=patch,
        )


def _list_assignments_for_model(
    policies_client: PoliciesV1Api,
    model_id: str,
) -> List[PolicyAssignment]:
    assignments: List[PolicyAssignment] = []
    page = 1
    while True:
        resp = policies_client.list_model_policy_assignments(
            model_id=model_id,
            page=page,
            page_size=_PAGE_SIZE,
        )
        assignments.extend(resp.records)
        if len(resp.records) < _PAGE_SIZE:
            break
        page += 1
    return assignments
