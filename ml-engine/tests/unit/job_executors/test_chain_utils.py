from unittest.mock import Mock
from uuid import uuid4

from arthur_client.api_bindings import PolicyAssignmentJobChainPatch

from job_executors._chain_utils import stamp_chain_job_id


def _make_assignments_page(ids):
    """Build a mock paginated response with the given assignment ids."""
    page = Mock()
    page.records = [Mock(id=aid) for aid in ids]
    return page


def test_stamp_chain_job_id_explicit_assignment_stamps_only_that_one():
    """When the chain is bound to a specific assignment, the helper PATCHes
    that assignment exactly once and never lists model assignments."""
    policies_client = Mock()
    assignment_id = uuid4()
    spawned_id = str(uuid4())
    patch = PolicyAssignmentJobChainPatch(compliance_job_id=spawned_id)

    stamp_chain_job_id(
        policies_client=policies_client,
        model_id=str(uuid4()),
        explicit_assignment_id=assignment_id,
        patch=patch,
    )

    policies_client.list_model_policy_assignments.assert_not_called()
    policies_client.update_assignment_job_chain.assert_called_once_with(
        assignment_id=str(assignment_id),
        policy_assignment_job_chain_patch=patch,
    )


def test_stamp_chain_job_id_model_wide_fans_out_to_all_assignments():
    """When the chain is model-wide (no explicit assignment_id), the helper
    lists every assignment for the model and PATCHes each one with the same
    spawned downstream job id."""
    policies_client = Mock()
    model_id = str(uuid4())
    aid_1, aid_2, aid_3 = str(uuid4()), str(uuid4()), str(uuid4())
    policies_client.list_model_policy_assignments.return_value = (
        _make_assignments_page([aid_1, aid_2, aid_3])
    )
    spawned_id = str(uuid4())
    patch = PolicyAssignmentJobChainPatch(alerts_check_job_id=spawned_id)

    stamp_chain_job_id(
        policies_client=policies_client,
        model_id=model_id,
        explicit_assignment_id=None,
        patch=patch,
    )

    policies_client.list_model_policy_assignments.assert_called_once_with(
        model_id=model_id, page=1, page_size=100
    )
    assert policies_client.update_assignment_job_chain.call_count == 3
    stamped_ids = {
        call.kwargs["assignment_id"]
        for call in policies_client.update_assignment_job_chain.call_args_list
    }
    assert stamped_ids == {aid_1, aid_2, aid_3}
    for call in policies_client.update_assignment_job_chain.call_args_list:
        assert call.kwargs["policy_assignment_job_chain_patch"] is patch


def test_stamp_chain_job_id_model_wide_pages_until_short_page():
    """The model-wide list call paginates: keeps fetching while a full page
    of 100 comes back, stops on the first short page."""
    policies_client = Mock()
    full_page = [str(uuid4()) for _ in range(100)]
    short_page = [str(uuid4()) for _ in range(7)]
    policies_client.list_model_policy_assignments.side_effect = [
        _make_assignments_page(full_page),
        _make_assignments_page(short_page),
    ]

    stamp_chain_job_id(
        policies_client=policies_client,
        model_id=str(uuid4()),
        explicit_assignment_id=None,
        patch=PolicyAssignmentJobChainPatch(alerts_check_job_id=str(uuid4())),
    )

    assert policies_client.list_model_policy_assignments.call_count == 2
    assert policies_client.update_assignment_job_chain.call_count == 107


def test_stamp_chain_job_id_model_wide_with_no_assignments_is_a_noop():
    """Empty model — no assignments to stamp, no PATCH calls."""
    policies_client = Mock()
    policies_client.list_model_policy_assignments.return_value = (
        _make_assignments_page([])
    )

    stamp_chain_job_id(
        policies_client=policies_client,
        model_id=str(uuid4()),
        explicit_assignment_id=None,
        patch=PolicyAssignmentJobChainPatch(compliance_job_id=str(uuid4())),
    )

    policies_client.update_assignment_job_chain.assert_not_called()
