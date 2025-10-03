import os
import random
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from arthur_common.models.enums import RuleResultEnum, RuleType
from arthur_common.models.response_schemas import QueryInferencesResponse

from db_models import DatabaseInference
from schemas.internal_schemas import InferencePrompt, Task
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.mocks.mock_scorer_client import (
    MOCK_KEYWORD_FAILING_TEXT,
    MOCK_KEYWORD_PASSING_TEXT,
    MOCK_REGEX_PASSING_TEXT,
)
from utils import constants


@pytest.mark.unit_tests
def test_query_happy_path(client: GenaiEngineTestClientBase):
    inference_ids = []
    for _ in range(10):
        status_code, prompt_result = client.create_prompt(
            "Prompt%s" % random.randint(0, 100),
        )
        assert status_code == 200
        new_inference_id = prompt_result.inference_id
        inference_ids.append(new_inference_id)
        status_code, response_result = client.create_response(
            new_inference_id,
            "Response123",
        )
        assert status_code == 200

    inference_ids.reverse()
    status_code, query_resp = client.query_inferences()
    assert status_code == 200

    # Default page size
    assert 10 == len(query_resp.inferences)
    assert inference_ids[:10] == [i.id for i in query_resp.inferences]
    assert query_resp.count > 2


@pytest.mark.unit_tests
def test_query_count_toggle(client: GenaiEngineTestClientBase):
    inference_ids = []
    for _ in range(10):
        status_code, prompt_result = client.create_prompt(
            "Prompt%s" % random.randint(0, 100),
        )
        assert status_code == 200
        new_inference_id = prompt_result.inference_id
        inference_ids.append(new_inference_id)
        status_code, response_result = client.create_response(
            new_inference_id,
            "Response123",
        )
        assert status_code == 200

    inference_ids.reverse()
    status_code, query_resp = client.query_inferences(include_count=False)
    assert status_code == 200

    # Default page size
    assert 10 == len(query_resp.inferences)
    assert inference_ids[:10] == [i.id for i in query_resp.inferences]
    assert query_resp.count == -1


@pytest.mark.unit_tests
def test_query_page_size_parameter(client: GenaiEngineTestClientBase):
    status_code, query_resp = client.query_inferences(page_size=5001)
    assert status_code == 400


@pytest.mark.unit_tests
def test_query_conversation_filter(client: GenaiEngineTestClientBase):
    inference_ids = []
    conversation_id = "conversationid%s" % random.random()
    for _ in range(10):
        status_code, prompt_result = client.create_prompt(
            "Prompt%s" % random.randint(0, 100),
            conversation_id=conversation_id,
        )
        assert status_code == 200
        new_inference_id = prompt_result.inference_id
        inference_ids.append(new_inference_id)
        status_code, response_result = client.create_response(
            new_inference_id,
            "Response123",
        )
        assert status_code == 200

    status_code, query_resp = client.query_inferences(conversation_id=conversation_id)
    assert status_code == 200
    assert all([i.conversation_id == conversation_id for i in query_resp.inferences])


@pytest.mark.unit_tests
def test_query_task_filter(client: GenaiEngineTestClientBase):
    task_name = "test_task%s" % random.random()
    status_code, task_response = client.create_task(task_name)
    assert status_code == 200

    inference_ids = []
    task_id = task_response.id
    for _ in range(10):
        status_code, prompt_result = client.create_prompt(
            "Prompt%s" % random.randint(0, 100),
            task_id=task_id,
        )
        assert status_code == 200
        new_inference_id = prompt_result.inference_id
        inference_ids.append(new_inference_id)
        status_code, response_result = client.create_response(
            new_inference_id,
            "Response123",
        )
        assert status_code == 200

    status_code, query_resp = client.query_inferences(task_ids=[task_id])
    assert status_code == 200

    assert all([i.task_id == task_id for i in query_resp.inferences])
    assert all([i.task_name == task_name for i in query_resp.inferences])


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [
        [None, None],
        [datetime.now() + timedelta(days=1), None],
        [None, datetime.now() - timedelta(days=1)],
        [datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=1)],
    ],
)
def test_query_date_filter(
    start_time: datetime | None,
    end_time: datetime | None,
    client: GenaiEngineTestClientBase,
):
    status_code, task_response = client.create_task("test_task%s" % random.random())
    assert status_code == 200

    inference_ids = []
    task_id = task_response.id
    for _ in range(10):
        status_code, prompt_result = client.create_prompt(
            "Prompt%s" % random.randint(0, 100),
            task_id=task_id,
        )
        assert status_code == 200
        new_inference_id = prompt_result.inference_id
        inference_ids.append(new_inference_id)
        status_code, response_result = client.create_response(
            new_inference_id,
            "Response123",
        )
        assert status_code == 200

    status_code, query_resp = client.query_inferences(
        task_ids=[task_id],
        start_time=start_time,
        end_time=end_time,
    )
    inferences = query_resp.inferences

    assert all([i.task_id == task_id for i in inferences])

    if start_time and end_time:
        assert len(inferences) > 0
    elif start_time:
        assert len(inferences) == 0
    elif end_time:
        assert len(inferences) == 0


@pytest.mark.unit_tests
def test_query_missing_responses(client: GenaiEngineTestClientBase):
    inference_ids = []
    k = 3
    for _ in range(k):
        status_code, prompt_result = client.create_prompt(
            "Prompt%s" % random.randint(0, 100),
        )
        assert status_code == 200
        new_inference_id = prompt_result.inference_id
        inference_ids.append(new_inference_id)

    inference_ids.reverse()
    status_code, query_resp = client.query_inferences(sort="desc", page_size=k)

    assert status_code == 200
    assert inference_ids == [i.id for i in query_resp.inferences]
    assert query_resp.count > 2


@pytest.mark.unit_tests
def test_query_sorting(client: GenaiEngineTestClientBase):
    inference_ids = []
    k = 3
    for _ in range(k):
        status_code, prompt_result = client.create_prompt(
            "Prompt%s" % random.randint(0, 100),
        )
        assert status_code == 200
        new_inference_id = prompt_result.inference_id
        inference_ids.append(new_inference_id)
        status_code, response_result = client.create_response(
            new_inference_id,
            "Response123",
        )
        assert status_code == 200

    query_resp = client.query_all_inferences(sort="asc")
    assert inference_ids == [i.id for i in query_resp.inferences[-1 * k :]]
    assert query_resp.count > 2


@pytest.mark.unit_tests
def test_query_paging(client: GenaiEngineTestClientBase):
    inference_ids = []
    for _ in range(4):
        status_code, prompt_result = client.create_prompt(
            "Prompt%s" % random.randint(0, 100),
        )
        assert status_code == 200
        new_inference_id = prompt_result.inference_id
        inference_ids.append(new_inference_id)
        status_code, response_result = client.create_response(
            new_inference_id,
            "Response123",
        )
        assert status_code == 200

    inference_ids.reverse()
    status_code, query_resp = client.query_inferences(sort="desc", page=0, page_size=2)

    assert status_code == 200
    assert len(query_resp.inferences) == 2
    assert set(list(inference_ids[:2])) == set([i.id for i in query_resp.inferences])
    assert query_resp.count > 2

    status_code, query_resp = client.query_inferences(sort="desc", page=1, page_size=2)

    assert status_code == 200
    assert len(query_resp.inferences) == 2
    assert set(list(inference_ids[2:])) == set([i.id for i in query_resp.inferences])
    assert query_resp.count > 2


@pytest.mark.unit_tests
def test_query_inference_contents_not_present_when_disabled(
    client: GenaiEngineTestClientBase,
):
    os.environ[constants.GENAI_ENGINE_ENABLE_PERSISTENCE_ENV_VAR] = "disabled"
    inference_ids = []
    sc, task = client.create_task(empty_rules=True)
    assert sc == 200
    sc, rule = client.create_rule("", RuleType.REGEX)
    assert sc == 200

    status_code, prompt_result = client.create_prompt("Prompt0", task_id=task.id)
    assert status_code == 200

    new_inference_id = prompt_result.inference_id
    inference_ids.append(new_inference_id)
    status_code, response_result = client.create_response(
        new_inference_id,
        "Response0",
        task_id=task.id,
    )

    assert status_code == 200

    assert len(prompt_result.rule_results) > 0
    for rr in prompt_result.rule_results:
        assert rr.result == RuleResultEnum.FAIL
        assert len(rr.details.regex_matches) > 0
        for rm in rr.details.regex_matches:
            assert rm.matching_text != ""

    assert len(response_result.rule_results) > 0
    for rr in response_result.rule_results:
        assert rr.result == RuleResultEnum.FAIL
        assert len(rr.details.regex_matches) > 0
        for rm in rr.details.regex_matches:
            assert rm.matching_text != ""

    status_code, query_resp = client.query_inferences(sort="desc", page_size=1)
    assert status_code == 200
    inference = query_resp.inferences[0]

    assert len(inference.inference_prompt.prompt_rule_results) > 0
    for rr in inference.inference_prompt.prompt_rule_results:
        assert rr.result == RuleResultEnum.FAIL
        assert len(rr.details.regex_matches) > 0
        for rm in rr.details.regex_matches:
            assert rm.matching_text == ""

    assert len(inference.inference_response.response_rule_results) > 0
    for rr in inference.inference_response.response_rule_results:
        assert rr.result == RuleResultEnum.FAIL
        assert len(rr.details.regex_matches) > 0
        for rm in rr.details.regex_matches:
            assert rm.matching_text == ""

    assert inference.inference_prompt.message == ""
    assert inference.inference_response.message == ""

    # Restore to default enablement
    os.environ[constants.GENAI_ENGINE_ENABLE_PERSISTENCE_ENV_VAR] = "enabled"


@pytest.mark.unit_tests
def test_query_inference_contents_contexts_present(client: GenaiEngineTestClientBase):
    inference_ids = []
    k = 3
    for i in range(k):
        status_code, prompt_result = client.create_prompt("Prompt%d" % i)
        assert status_code == 200
        new_inference_id = prompt_result.inference_id
        inference_ids.append(new_inference_id)
        status_code, _ = client.create_response(
            new_inference_id,
            f"Response{i}",
            context=f"Context{i}",
        )
        assert status_code == 200

    status_code, query_resp = client.query_inferences(sort="desc", page_size=k)
    assert status_code == 200

    prompts = [i.inference_prompt.message for i in query_resp.inferences]
    responses = [i.inference_response.message for i in query_resp.inferences]
    contexts = [i.inference_response.context for i in query_resp.inferences]
    for i in range(k):
        assert f"Prompt{i}" in prompts
        assert f"Response{i}" in responses
        assert f"Context{i}" in contexts

    assert query_resp.count > 2


@patch("config.cache_config.cache_config.TASK_RULES_CACHE_ENABLED", False)
@pytest.mark.parametrize(
    (
        "rule_types",
        "rule_statuses",
        "prompt_statuses",
        "response_statuses",
        "expected_status_code",
        "expected_count",
    ),
    [
        [None, None, None, None, 200, 5],
        [[RuleType.TOXICITY], None, None, None, 200, 1],
        [[RuleType.REGEX], None, None, None, 200, 3],
        [[RuleType.KEYWORD], None, None, None, 200, 3],
        [[RuleType.PROMPT_INJECTION], None, None, None, 200, 3],
        [None, [RuleResultEnum.FAIL], None, None, 200, 2],
        [[RuleType.REGEX], [RuleResultEnum.FAIL], None, None, 200, 0],
        [[RuleType.KEYWORD], [RuleResultEnum.FAIL], None, None, 200, 2],
        [[RuleType.KEYWORD], [RuleResultEnum.PASS], None, None, 200, 3],
        [[RuleType.REGEX], None, [RuleResultEnum.PASS], None, 200, 2],
        [[RuleType.REGEX], None, [RuleResultEnum.FAIL], None, 200, 1],
        [None, None, [RuleResultEnum.FAIL, RuleResultEnum.PASS], None, 200, 5],
        [
            None,
            None,
            [RuleResultEnum.FAIL, RuleResultEnum.PASS],
            [RuleResultEnum.FAIL, RuleResultEnum.PASS],
            200,
            4,
        ],
        [None, None, None, [RuleResultEnum.FAIL], 200, 1],
    ],
)
@pytest.mark.unit_tests
def test_query_rule_status_filters(
    rule_types: list[RuleType],
    rule_statuses: list[RuleResultEnum],
    prompt_statuses: list[RuleResultEnum],
    response_statuses: list[RuleResultEnum],
    expected_status_code: int,
    expected_count: int,
    client: GenaiEngineTestClientBase,
):
    print("PYTEST_CURRENT_TEST: ", "PYTEST_CURRENT_TEST" not in os.environ)
    _, task = client.create_task(empty_rules=True)
    _, hall_rule = client.create_rule(
        "",
        rule_type=RuleType.TOXICITY,
        task_id=task.id,
        response_enabled=True,
        prompt_enabled=False,
    )

    fail_text = " ".join([MOCK_REGEX_PASSING_TEXT, MOCK_KEYWORD_FAILING_TEXT])
    pass_text = " ".join([MOCK_REGEX_PASSING_TEXT, MOCK_KEYWORD_PASSING_TEXT])

    # Create all passing inference with other type rule run
    _, prompt = client.create_prompt(pass_text, task_id=task.id)
    print("Empty inference id: ", prompt.inference_id)
    _, response = client.create_response(
        prompt.inference_id,
        pass_text,
        task_id=task.id,
    )
    _, client.patch_rule(task_id=task.id, rule_id=hall_rule.id, enabled=False)

    # Create inference with no response
    _, prompt = client.create_prompt(pass_text, task_id=task.id)

    _, _ = client.create_rule(
        "",
        rule_type=RuleType.REGEX,
        task_id=task.id,
        regex_patterns=["\\*AlwaysPass"],
    )
    _, _ = client.create_rule(
        "",
        rule_type=RuleType.KEYWORD,
        task_id=task.id,
        keywords=[MOCK_KEYWORD_FAILING_TEXT],
    )
    _, _ = client.create_rule("", rule_type=RuleType.PROMPT_INJECTION, task_id=task.id)

    # Create all passing inference
    _, prompt = client.create_prompt(pass_text, task_id=task.id)
    print("Passing inference id: ", prompt.inference_id)
    _, response = client.create_response(
        prompt.inference_id,
        pass_text,
        task_id=task.id,
    )

    # Create failing keyword prompt inference
    _, prompt = client.create_prompt(fail_text, task_id=task.id)
    print("Failing prompt inference id: ", prompt.inference_id)
    _, response = client.create_response(
        prompt.inference_id,
        pass_text,
        task_id=task.id,
    )

    # Create failing keyword response inference
    _, prompt = client.create_prompt(pass_text, task_id=task.id)
    print("Failing response inference id: ", prompt.inference_id)
    _, response = client.create_response(
        prompt.inference_id,
        fail_text,
        task_id=task.id,
    )

    status_code, results = client.query_inferences(
        task_ids=[task.id],
        rule_types=rule_types,
        rule_statuses=rule_statuses,
        prompt_results=prompt_statuses,
        response_results=response_statuses,
        sort="asc",
    )

    assert status_code == expected_status_code

    if expected_status_code != 200:
        return

    assert results.count == expected_count
    assert len(results.inferences) == expected_count

    for inference in results.inferences:
        if prompt_statuses:
            assert inference.inference_prompt.result in prompt_statuses
        if response_statuses:
            assert inference.inference_response.result in response_statuses
        if rule_statuses:
            assert any(
                [
                    rr.result in rule_statuses
                    for rr in inference.inference_prompt.prompt_rule_results
                ]
                + [
                    rr.result in rule_statuses
                    for rr in inference.inference_response.response_rule_results
                ],
            )
        if rule_types:
            assert any(
                [
                    rr.rule_type in rule_types
                    for rr in inference.inference_prompt.prompt_rule_results
                ]
                + [
                    rr.rule_type in rule_types
                    for rr in inference.inference_response.response_rule_results
                ],
            )


@pytest.mark.unit_tests
def test_query_inference_hidden_components_not_present(
    client: GenaiEngineTestClientBase,
):
    inference_ids = []
    k = 1
    for i in range(k):
        status_code, prompt_result = client.create_prompt("Prompt%d" % i)
        assert status_code == 200
        new_inference_id = prompt_result.inference_id
        inference_ids.append(new_inference_id)
        status_code, response_result = client.create_response(
            new_inference_id,
            "Response%d" % i,
        )
        assert status_code == 200

    status_code, query_resp = client.query_inferences(sort="desc", page_size=k)

    assert status_code == 200
    assert query_resp.count > 2


@pytest.mark.unit_tests
def test_query_inference_with_user_id(
    create_prompt_inference,
    client: GenaiEngineTestClientBase,
):
    created_prompt = create_prompt_inference
    user_id = "genai_engine_user"
    status_code: int
    query_resp: QueryInferencesResponse
    status_code, query_resp = client.query_inferences(user_id=user_id)

    assert status_code == 200
    assert query_resp.count == 1
    assert query_resp.inferences[0].id == created_prompt.inference_id
    assert query_resp.inferences[0].inference_prompt.id == created_prompt.id
    assert query_resp.inferences[0].inference_prompt.message == created_prompt.message
    assert query_resp.inferences[0].user_id == user_id


@pytest.mark.unit_tests
def test_query_inference_by_id(
    create_prompt_inference,
    client: GenaiEngineTestClientBase,
):
    created_prompt = create_prompt_inference
    status_code: int
    query_resp: QueryInferencesResponse
    status_code, query_resp = client.query_inferences(
        inference_id=created_prompt.inference_id,
    )

    assert status_code == 200
    assert query_resp.count == 1
    assert query_resp.inferences[0].id == created_prompt.inference_id


@pytest.mark.unit_tests
def test_query_inference_by_id_if_not_exist(client: GenaiEngineTestClientBase):
    status_code: int
    query_resp: QueryInferencesResponse
    status_code, query_resp = client.query_inferences(
        inference_id="not-existing-inference",
    )

    assert status_code == 200
    assert query_resp.count == 0
    assert query_resp.inferences == []


@pytest.mark.unit_tests
def test_query_inference_by_task_name(
    create_prompt_inference_with_task,
    client: GenaiEngineTestClientBase,
):
    task, inference = create_prompt_inference_with_task
    status_code: int
    query_resp: QueryInferencesResponse

    status_code, query_resp = client.query_inferences(task_name=task.name)
    assert status_code == 200
    assert query_resp.count == 1
    assert query_resp.inferences[0].task_name == task.name

    status_code, query_resp = client.query_inferences(task_name=task.name.upper())
    assert status_code == 200
    assert query_resp.count == 1
    assert query_resp.inferences[0].task_name == task.name

    status_code, query_resp = client.query_inferences(task_name=task.name.lower())
    assert status_code == 200
    assert query_resp.count == 1
    assert query_resp.inferences[0].task_name == task.name


@pytest.mark.unit_tests
def test_query_inference_by_task_name_if_task_is_not_linked(
    create_task: Task,
    create_prompt_inference: InferencePrompt,
    client: GenaiEngineTestClientBase,
):
    status_code: int
    query_resp: QueryInferencesResponse
    status_code, query_resp = client.query_inferences(task_name=create_task.name)

    assert status_code == 200
    assert query_resp.count == 0
    assert query_resp.inferences == []


@pytest.mark.unit_tests
def test_query_inferency_sort_claims(
    create_inference_with_prompt_and_response: DatabaseInference,
    client: GenaiEngineTestClientBase,
):
    created_inference = create_inference_with_prompt_and_response
    status_code: int
    query_resp: QueryInferencesResponse
    status_code, query_resp = client.query_inferences(inference_id=created_inference.id)

    assert status_code == 200

    claims = (
        query_resp.inferences[0]
        .inference_response.response_rule_results[0]
        .details.claims
    )
    assert len(claims) == 3
    assert claims[0].order_number == 0
    assert claims[0].claim == "Is this just fantasy?"
    assert claims[1].order_number == 1
    assert claims[1].claim == "Caught in a landslide,"
    assert claims[2].order_number == 2
    assert claims[2].claim == "no escape from reality"
