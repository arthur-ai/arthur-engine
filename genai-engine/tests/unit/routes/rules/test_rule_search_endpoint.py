import pytest
from arthur_common.models.enums import PaginationSortMethod, RuleScope, RuleType
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    (
        "sort",
        "page",
        "page_size",
        "rule_scopes",
        "prompt_enabled",
        "response_enabled",
        "rule_types",
    ),
    [
        [None, None, None, None, None, None, None],
        [None, None, 4, None, None, None, None],
        [None, None, 20, [RuleScope.DEFAULT], None, None, None],
        [None, None, 20, [RuleScope.DEFAULT], True, None, None],
        [None, None, 20, [RuleScope.DEFAULT], True, False, None],
        [
            None,
            None,
            20,
            [RuleScope.DEFAULT],
            True,
            False,
            [RuleType.REGEX, RuleType.KEYWORD],
        ],
        [
            PaginationSortMethod.ASCENDING,
            None,
            20,
            [RuleScope.DEFAULT],
            True,
            False,
            [RuleType.REGEX, RuleType.KEYWORD],
        ],
    ],
)
def test_search_rules(
    sort: PaginationSortMethod,
    page: int,
    page_size: int,
    rule_scopes: list[RuleScope],
    prompt_enabled: bool,
    response_enabled: bool,
    rule_types: list[RuleType],
    client: GenaiEngineTestClientBase,
):
    request_ids = []
    sc, task = client.create_task()
    assert sc == 200
    for rule_type in [RuleType.REGEX, RuleType.KEYWORD, RuleType.PII_DATA]:
        for pe in [True, False]:
            for re in [True, False]:
                if not pe and not re:
                    continue
                for rule_scope in [RuleScope.TASK, RuleScope.DEFAULT]:
                    sc, rule = client.create_rule(
                        "",
                        rule_type=rule_type,
                        prompt_enabled=pe,
                        response_enabled=re,
                        task_id=task.id if rule_scope == RuleScope.TASK else None,
                    )
                    assert sc == 200
                    request_ids.append(rule.id)

    sc, rules_resp = client.search_rules(
        sort=sort,
        page=page,
        page_size=page_size,
        prompt_enabled=prompt_enabled,
        response_enabled=response_enabled,
        rule_scopes=rule_scopes,
        rule_types=rule_types,
    )
    assert sc == 200

    rules = rules_resp.rules
    if len(rules) > 0:
        t = rules[0]
        if sort == PaginationSortMethod.DESCENDING or sort is None:
            for i in rules[1:]:
                assert i.created_at < t.created_at
                t = i
        elif sort == PaginationSortMethod.ASCENDING:
            for i in rules[1:]:
                assert i.created_at > t.created_at
                t = i

    if page_size:
        assert len(rules) <= page_size

    for r in rules:
        if rule_scopes:
            assert r.scope in rule_scopes
        if prompt_enabled:
            assert r.apply_to_prompt == prompt_enabled
        if response_enabled:
            assert r.apply_to_response == response_enabled
        if rule_types:
            assert r.type in rule_types
