from unittest.mock import Mock
from uuid import uuid4

from arthur_client.api_bindings import PolicyAssignmentJobChainPatch

from job_executors._chain_utils import stamp_chain_job_id


def _assignment(assignment_id, *, metrics_calc_job_id=None, alerts_check_job_id=None):
    """A policy assignment as the client returns it, with the chain jobs it carries."""
    return Mock(
        id=assignment_id,
        metrics_calc_job=Mock(id=metrics_calc_job_id) if metrics_calc_job_id else None,
        alerts_check_job=Mock(id=alerts_check_job_id) if alerts_check_job_id else None,
    )


def _page(assignments):
    page = Mock()
    page.records = assignments
    return page


def test_explicit_assignment_is_stamped_when_this_job_heads_its_chain():
    """Bound to one assignment, the helper PATCHes that assignment once, because
    its alert-check stage is this job, and leaves the model's others alone even
    when this job heads them too (a per-assignment check is for one assignment)."""
    policies_client = Mock()
    assignment_id = uuid4()
    job_id = str(uuid4())
    policies_client.list_model_policy_assignments.return_value = _page(
        [
            _assignment(str(assignment_id), alerts_check_job_id=job_id),
            _assignment(str(uuid4()), alerts_check_job_id=job_id),
        ]
    )
    patch = PolicyAssignmentJobChainPatch(compliance_job_id=str(uuid4()))

    stamp_chain_job_id(
        policies_client=policies_client,
        model_id=str(uuid4()),
        explicit_assignment_id=assignment_id,
        patch=patch,
        current_job_id=job_id,
        previous_stage="alerts_check_job",
    )

    policies_client.update_assignment_job_chain.assert_called_once_with(
        assignment_id=str(assignment_id),
        policy_assignment_job_chain_patch=patch,
    )


def test_explicit_assignment_is_left_alone_when_another_chain_took_it_over():
    """The user restarted the check while this chain was still running: the
    assignment's alert-check stage is a newer job, so this job's stamp is stale."""
    policies_client = Mock()
    assignment_id = uuid4()
    policies_client.list_model_policy_assignments.return_value = _page(
        [_assignment(str(assignment_id), alerts_check_job_id=str(uuid4()))]
    )

    stamp_chain_job_id(
        policies_client=policies_client,
        model_id=str(uuid4()),
        explicit_assignment_id=assignment_id,
        patch=PolicyAssignmentJobChainPatch(compliance_job_id=str(uuid4())),
        current_job_id=str(uuid4()),
        previous_stage="alerts_check_job",
    )

    policies_client.update_assignment_job_chain.assert_not_called()


def test_model_wide_chain_stamps_only_the_assignments_it_heads():
    """A model-wide check stamps metrics_calc_job_id on every assignment it
    covers, so each of those is advanced; an assignment whose chain head is some
    other job (a check started separately) is not."""
    policies_client = Mock()
    model_id = str(uuid4())
    job_id = str(uuid4())
    aid_1, aid_2, other = str(uuid4()), str(uuid4()), str(uuid4())
    policies_client.list_model_policy_assignments.return_value = _page(
        [
            _assignment(aid_1, metrics_calc_job_id=job_id),
            _assignment(aid_2, metrics_calc_job_id=job_id),
            _assignment(other, metrics_calc_job_id=str(uuid4())),
        ]
    )
    patch = PolicyAssignmentJobChainPatch(alerts_check_job_id=str(uuid4()))

    stamp_chain_job_id(
        policies_client=policies_client,
        model_id=model_id,
        explicit_assignment_id=None,
        patch=patch,
        current_job_id=job_id,
        previous_stage="metrics_calc_job",
    )

    policies_client.list_model_policy_assignments.assert_called_once_with(
        model_id=model_id, page=1, page_size=100
    )
    stamped_ids = {
        call.kwargs["assignment_id"]
        for call in policies_client.update_assignment_job_chain.call_args_list
    }
    assert stamped_ids == {aid_1, aid_2}
    for call in policies_client.update_assignment_job_chain.call_args_list:
        assert call.kwargs["policy_assignment_job_chain_patch"] is patch


def test_scheduled_run_heads_no_chain_and_stamps_nothing():
    """A scheduled metrics run has no assignment of its own; the assignments on
    the model carry the chains of user checks, which must not be advanced."""
    policies_client = Mock()
    policies_client.list_model_policy_assignments.return_value = _page(
        [
            _assignment(str(uuid4()), metrics_calc_job_id=str(uuid4())),
            _assignment(str(uuid4())),
        ]
    )

    stamp_chain_job_id(
        policies_client=policies_client,
        model_id=str(uuid4()),
        explicit_assignment_id=None,
        patch=PolicyAssignmentJobChainPatch(alerts_check_job_id=str(uuid4())),
        current_job_id=str(uuid4()),
        previous_stage="metrics_calc_job",
    )

    policies_client.update_assignment_job_chain.assert_not_called()


def test_model_wide_listing_pages_until_a_short_page():
    """The model-wide list call paginates: keeps fetching while a full page of
    100 comes back, stops on the first short page, and stamps across pages."""
    policies_client = Mock()
    job_id = str(uuid4())
    full_page = [
        _assignment(str(uuid4()), metrics_calc_job_id=job_id) for _ in range(100)
    ]
    short_page = [
        _assignment(str(uuid4()), metrics_calc_job_id=job_id) for _ in range(7)
    ]
    policies_client.list_model_policy_assignments.side_effect = [
        _page(full_page),
        _page(short_page),
    ]

    stamp_chain_job_id(
        policies_client=policies_client,
        model_id=str(uuid4()),
        explicit_assignment_id=None,
        patch=PolicyAssignmentJobChainPatch(alerts_check_job_id=str(uuid4())),
        current_job_id=job_id,
        previous_stage="metrics_calc_job",
    )

    assert policies_client.list_model_policy_assignments.call_count == 2
    assert policies_client.update_assignment_job_chain.call_count == 107


def test_model_with_no_assignments_is_a_noop():
    policies_client = Mock()
    policies_client.list_model_policy_assignments.return_value = _page([])

    stamp_chain_job_id(
        policies_client=policies_client,
        model_id=str(uuid4()),
        explicit_assignment_id=None,
        patch=PolicyAssignmentJobChainPatch(compliance_job_id=str(uuid4())),
        current_job_id=str(uuid4()),
        previous_stage="metrics_calc_job",
    )

    policies_client.update_assignment_job_chain.assert_not_called()
