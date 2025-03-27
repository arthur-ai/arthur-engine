import math
import random
from uuid import uuid4

import pytest
from pydantic import ValidationError
from schemas.common_schemas import ExamplesConfig, PIIConfig, ToxicityConfig
from schemas.enums import PIIEntityTypes, RuleResultEnum, RuleScope, RuleType
from schemas.internal_schemas import Rule
from tests.clients.base_test_client import (
    DEFAULT_KEYWORDS,
    DEFAULT_REGEX,
    GenaiEngineTestClientBase,
)


@pytest.mark.unit_tests
def test_create_regex_rule(client: GenaiEngineTestClientBase):
    status_code, rule = client.create_rule("regex123", RuleType.REGEX)
    assert status_code == 200

    assert rule.name == "regex123"
    assert rule.type == "RegexRule"
    assert rule.scope == RuleScope.DEFAULT

    assert rule.config.regex_patterns is not None
    assert rule.config.regex_patterns == DEFAULT_REGEX
    assert rule.created_at
    assert rule.updated_at

    return rule


@pytest.mark.unit_tests
def test_create_regex_rule_fail(client: GenaiEngineTestClientBase):
    status_code, _ = client.create_rule("regex123", RuleType.REGEX, skip_config=True)
    assert status_code == 400


@pytest.mark.unit_tests
def test_create_keyword_rule(client: GenaiEngineTestClientBase):
    status_code, rule = client.create_rule("keyword123", RuleType.KEYWORD)
    assert status_code == 200

    assert rule.name == "keyword123"
    assert rule.type == "KeywordRule"
    assert rule.scope == RuleScope.DEFAULT
    assert rule.config.keywords is not None
    assert set(rule.config.keywords) == set(DEFAULT_KEYWORDS)
    assert rule.created_at
    assert rule.updated_at

    return rule


@pytest.mark.unit_tests
def test_create_keyword_rule_fail(client: GenaiEngineTestClientBase):
    status_code, rule = client.create_rule(
        "keyword123",
        RuleType.KEYWORD,
        skip_config=True,
    )
    assert status_code == 400


@pytest.mark.unit_tests
def test_create_sensitive_data_rule(client: GenaiEngineTestClientBase):
    status_code, rule = client.create_rule(
        "sensitive_data123",
        RuleType.MODEL_SENSITIVE_DATA,
        response_enabled=False,
    )
    assert status_code == 200
    assert rule.id
    assert rule.name == "sensitive_data123"
    assert rule.type == "ModelSensitiveDataRule"
    assert rule.scope == RuleScope.DEFAULT
    assert rule.config is not None
    assert type(rule.config) is ExamplesConfig
    assert rule.created_at
    assert rule.updated_at

    return rule


@pytest.mark.unit_tests
def test_create_sensitive_data_rule_examples_required(
    client: GenaiEngineTestClientBase,
):
    status_code, error = client.create_rule(
        "sensitive_data123",
        RuleType.MODEL_SENSITIVE_DATA,
        examples=[],
        response_enabled=False,
    )
    assert status_code == 400
    assert (
        error["detail"]
        == "Examples must be provided to onboard a ModelSensitiveDataRule"
    )


@pytest.mark.unit_tests
def test_create_sensitive_data_rule_response_enabled(client: GenaiEngineTestClientBase):
    status_code, error = client.create_rule(
        "sensitive_data123",
        RuleType.MODEL_SENSITIVE_DATA,
        examples=[],
        response_enabled=True,
    )
    assert status_code == 400
    assert (
        error["detail"].replace("\n", "")
        == "ModelSensitiveDataRule can only be enabled for prompt. Please set the 'apply_to_response' field to false."
    )


@pytest.mark.unit_tests
def test_create_hallucination_v2_rule(client: GenaiEngineTestClientBase):
    status_code, rule = client.create_rule(
        "Hallucination_V2",
        RuleType.MODEL_HALLUCINATION_V2,
        prompt_enabled=False,
    )
    assert status_code == 200

    assert rule.name == "Hallucination_V2"
    assert rule.type == RuleType.MODEL_HALLUCINATION_V2
    assert rule.scope == RuleScope.DEFAULT
    assert rule.created_at
    assert rule.updated_at


@pytest.mark.unit_tests
def test_create_hallucination_v2_rule_prompt_enabled(client: GenaiEngineTestClientBase):
    status_code, error = client.create_rule(
        "Hallucination_V2",
        RuleType.MODEL_HALLUCINATION_V2,
        prompt_enabled=True,
    )
    assert status_code == 400
    assert (
        error["detail"]
        == "ModelHallucinationRuleV2 can only be enabled for response. Please set the 'apply_to_prompt' field to false."
    )


@pytest.mark.unit_tests
def test_create_toxicity_rule(client: GenaiEngineTestClientBase):
    status_code, rule = client.create_rule(
        "toxicity",
        RuleType.TOXICITY,
        prompt_enabled=True,
        toxicity_threshold=0.3,
    )
    assert status_code == 200

    assert rule.name == "toxicity"
    assert rule.type == RuleType.TOXICITY
    assert rule.scope == RuleScope.DEFAULT
    assert rule.config is not None
    assert type(rule.config) is ToxicityConfig
    assert rule.config.threshold == 0.3
    assert rule.created_at
    assert rule.updated_at


@pytest.mark.unit_tests
def test_create_toxicity_rule_fail(client: GenaiEngineTestClientBase):
    with pytest.raises(ValidationError):
        status_code, rule = client.create_rule(
            "toxicity",
            RuleType.TOXICITY,
            prompt_enabled=True,
            toxicity_threshold=1.3,
        )

    with pytest.raises(ValidationError):
        status_code, rule = client.create_rule(
            "toxicity",
            RuleType.TOXICITY,
            prompt_enabled=True,
            toxicity_threshold=-1.3,
        )


@pytest.mark.unit_tests
def test_user_story_create_get_delete_rule(client: GenaiEngineTestClientBase):
    regex_rule = test_create_regex_rule(client)
    keyword_rule = test_create_keyword_rule(client)

    status_code, rules_resp = client.search_rules(rule_scopes=[RuleScope.DEFAULT])
    rules = rules_resp.rules
    assert status_code == 200

    # New rules are returned
    assert regex_rule.id in [rule.id for rule in rules]
    assert keyword_rule.id in [rule.id for rule in rules]

    # Delete Rules
    status_code = client.delete_default_rule(regex_rule.id)
    assert status_code == 200
    status_code = client.delete_default_rule(keyword_rule.id)
    assert status_code == 200

    status_code, default_rules = client.search_rules(rule_scopes=[RuleScope.DEFAULT])
    default_rules = default_rules.rules
    assert status_code == 200

    # New rules are deleted
    assert regex_rule.id not in [rule.id for rule in default_rules]
    assert keyword_rule.id not in [rule.id for rule in default_rules]


@pytest.mark.unit_tests
def test_user_story_create_get_delete_task_rule(client: GenaiEngineTestClientBase):
    _, task = client.create_task()

    regex_rule = test_create_regex_rule(client)
    keyword_rule = test_create_keyword_rule(client)

    status_code, rules_resp = client.search_rules(rule_scopes=[RuleScope.DEFAULT])
    rules = rules_resp.rules
    assert status_code == 200
    _, task = client.get_task(task.id)
    # New rules in task
    assert regex_rule.id in [rule.id for rule in task.rules]
    assert keyword_rule.id in [rule.id for rule in task.rules]

    # New rules are returned
    assert regex_rule.id in [rule.id for rule in rules]
    assert keyword_rule.id in [rule.id for rule in rules]

    # Push prompt with this task to run default rules
    conversation_id = str(random.random())
    status_code, prompt_result = client.create_prompt(
        "",
        task_id=task.id,
        conversation_id=conversation_id,
    )
    assert status_code == 200

    # Delete Rules
    status_code = client.delete_default_rule(regex_rule.id)
    assert status_code == 200
    status_code = client.delete_default_rule(keyword_rule.id)
    assert status_code == 200

    status_code, default_rules_resp = client.search_rules(
        rule_scopes=[RuleScope.DEFAULT],
    )
    default_rules = default_rules_resp.rules
    assert status_code == 200

    # New rules are deleted
    assert regex_rule.id not in [rule.id for rule in default_rules]
    assert keyword_rule.id not in [rule.id for rule in default_rules]

    # Refresh task
    _, task = client.get_task(task.id)

    # New rules no longer in task
    assert regex_rule.id not in [rule.id for rule in task.rules]
    assert keyword_rule.id not in [rule.id for rule in task.rules]

    # Archived rules still in inference results
    _, inferences = client.query_inferences(conversation_id=conversation_id)
    for inference in inferences.inferences:
        prompt_rule_ids = [
            rule.id for rule in inference.inference_prompt.prompt_rule_results
        ]
        assert regex_rule.id in prompt_rule_ids
        assert keyword_rule.id in prompt_rule_ids


@pytest.mark.unit_tests
def test_delete_rule_not_exists(client: GenaiEngineTestClientBase):
    uuid_not_existing = uuid4()
    status_code = client.delete_default_rule(uuid_not_existing)
    assert status_code == 404


@pytest.mark.unit_tests
def test_user_story_create_rule_send_prompt(client: GenaiEngineTestClientBase):
    unique_keyword = "{}{}".format("keyword", random.random())
    status_code, keyword_rule = client.create_rule(
        unique_keyword,
        RuleType.KEYWORD,
        keywords=[unique_keyword],
    )
    assert status_code == 200

    status_code, prompt_result = client.create_prompt("cool prompt for this test")
    assert status_code == 200

    assert len(prompt_result.rule_results) > 0
    assert keyword_rule.id in [res.id for res in prompt_result.rule_results]
    for rr in prompt_result.rule_results:
        assert rr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]


@pytest.mark.unit_tests
def test_user_story_create_task_get_all_tasks(client: GenaiEngineTestClientBase):
    status_code, task_response = client.create_task("test_task")
    assert status_code == 200

    assert len(task_response.id) != 0
    assert task_response.name == "test_task"
    assert task_response.created_at
    assert task_response.updated_at
    assert task_response.created_at != 0
    assert task_response.updated_at != 0

    status_code, tasks_resp = client.search_tasks()
    tasks = tasks_resp.tasks
    assert status_code == 200

    assert task_response.id in [task.id for task in tasks]


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    ("count"),
    [
        pytest.param(None, marks=pytest.mark.unit_tests),
        pytest.param(8, marks=[pytest.mark.unit_tests, pytest.mark.integration_tests]),
    ],
)
def test_create_too_many_llm_rules(count, client: GenaiEngineTestClientBase):
    task_name = str(random.random())
    status_code, task_response = client.create_task(task_name, empty_rules=True)

    if count is None:
        count = 3
    else:
        config = {"max_llm_rules_per_task_count": count}
        update_resp = client.update_configs(
            config,
            headers=client.authorized_org_admin_api_key_headers,
        )
        assert update_resp.status_code == 200
        print(client.get_configs().json())

    for i in range(count):
        status_code, _ = client.create_rule(
            "",
            RuleType.MODEL_HALLUCINATION_V2,
            examples=[],
            prompt_enabled=False,
            task_id=task_response.id,
        )
        assert status_code == 200
    status_code, _ = client.create_rule(
        "",
        RuleType.MODEL_HALLUCINATION_V2,
        examples=[],
        prompt_enabled=False,
        task_id=task_response.id,
    )
    assert status_code == 400

    # Non-LLM rules should be allowed
    status_code, _ = client.create_rule("", RuleType.REGEX, task_id=task_response.id)
    assert status_code == 200


@pytest.mark.unit_tests
def test_user_story_create_default_rule_get_updated_tasks(
    client: GenaiEngineTestClientBase,
):
    i = 0
    num_tasks = 204
    while i <= num_tasks:
        task_name = f"test_task{i}"
        status_code, task_response = client.create_task(task_name)
        assert status_code == 200
        assert len(task_response.id) != 0
        assert task_response.name == task_name
        assert task_response.created_at
        assert task_response.updated_at
        assert task_response.created_at != 0
        assert task_response.updated_at != 0
        i += 1

    status_code, all_tasks = client.search_tasks(page_size=num_tasks)
    all_tasks = all_tasks.tasks

    assert status_code == 200
    assert num_tasks == len(all_tasks)

    assert task_response.id in [task.id for task in all_tasks]

    unique_keyword = "{}{}".format("keyword", random.random())
    status_code, _ = client.create_rule(
        unique_keyword,
        RuleType.KEYWORD,
        keywords=[unique_keyword],
    )
    assert status_code == 200

    status_code, post_rule_creation_tasks = client.search_tasks(page_size=num_tasks)
    post_rule_creation_tasks = post_rule_creation_tasks.tasks

    assert status_code == 200
    assert num_tasks == len(post_rule_creation_tasks)

    for post_rule_creation_task in post_rule_creation_tasks:
        for task in all_tasks:
            if task.id == post_rule_creation_task.id:
                assert len(post_rule_creation_task.rules) == len(task.rules) + 1


@pytest.mark.unit_tests
def test_create_pii_rule_default_confg(client: GenaiEngineTestClientBase):
    status_code, rule = client.create_rule(
        "pii_default_config",
        RuleType.PII_DATA,
        prompt_enabled=True,
    )
    assert status_code == 200

    assert rule.name == "pii_default_config"
    assert rule.type == RuleType.PII_DATA
    assert rule.scope == RuleScope.DEFAULT
    assert rule.config is not None
    assert type(rule.config) is PIIConfig
    assert rule.created_at
    assert rule.updated_at


@pytest.mark.unit_tests
def test_create_pii_rule_skip_config_input(client: GenaiEngineTestClientBase):
    status_code, rule = client.create_rule(
        "pii_skip_config_input",
        RuleType.PII_DATA,
        prompt_enabled=True,
        skip_config=True,
    )
    assert status_code == 200

    assert rule.name == "pii_skip_config_input"
    assert rule.type == RuleType.PII_DATA
    assert rule.scope == RuleScope.DEFAULT
    assert rule.config is not None
    assert type(rule.config) is PIIConfig
    assert math.isclose(rule.config.confidence_threshold, 0.0, rel_tol=1e-9)
    assert rule.created_at
    assert rule.updated_at


@pytest.mark.unit_tests
def test_create_pii_rule_exclude_entities(client: GenaiEngineTestClientBase):
    disabled_checks = [PIIEntityTypes.PERSON]
    status_code, rule = client.create_rule(
        "pii_exclude_PERSON",
        RuleType.PII_DATA,
        prompt_enabled=True,
        disabled_pii_entities=disabled_checks,
    )
    assert status_code == 200

    assert rule.name == "pii_exclude_PERSON"
    assert rule.type == RuleType.PII_DATA
    assert rule.scope == RuleScope.DEFAULT
    assert rule.config is not None
    assert type(rule.config) is PIIConfig
    assert rule.config.disabled_pii_entities == disabled_checks
    assert rule.created_at
    assert rule.updated_at


@pytest.mark.unit_tests
def test_create_pii_rule_exclude_entities_and_allow_list(
    client: GenaiEngineTestClientBase,
):
    disabled_checks = [PIIEntityTypes.PERSON, PIIEntityTypes.EMAIL_ADDRESS]
    allow_list = ["Arthur GenAI Engine", "support@arthur.ai"]
    status_code, rule = client.create_rule(
        "pii_exclude_PERSON_EMAIL_allow_list",
        RuleType.PII_DATA,
        prompt_enabled=True,
        disabled_pii_entities=disabled_checks,
        allow_list=allow_list,
    )
    assert status_code == 200

    assert rule.name == "pii_exclude_PERSON_EMAIL_allow_list"
    assert rule.type == RuleType.PII_DATA
    assert rule.scope == RuleScope.DEFAULT
    assert rule.config is not None
    assert type(rule.config) is PIIConfig
    assert rule.config.disabled_pii_entities == disabled_checks
    assert rule.config.allow_list == allow_list
    assert rule.created_at
    assert rule.updated_at


@pytest.mark.unit_tests
def test_create_pii_rule_exclude_entities_and_allow_list_and_threshold(
    client: GenaiEngineTestClientBase,
):
    disabled_checks = [PIIEntityTypes.IP_ADDRESS, PIIEntityTypes.URL]
    allow_list = ["Joe", "test@test.com"]
    threshold = 0.2
    status_code, rule = client.create_rule(
        "pii_exclude_all_fields_in_config",
        RuleType.PII_DATA,
        prompt_enabled=True,
        disabled_pii_entities=disabled_checks,
        allow_list=allow_list,
        pii_confidence_threshold=threshold,
    )
    assert status_code == 200

    assert rule.name == "pii_exclude_all_fields_in_config"
    assert rule.type == RuleType.PII_DATA
    assert rule.scope == RuleScope.DEFAULT
    assert rule.config is not None
    assert type(rule.config) is PIIConfig
    assert rule.config.confidence_threshold == threshold
    assert rule.config.disabled_pii_entities == disabled_checks
    assert rule.config.allow_list == allow_list
    assert rule.created_at
    assert rule.updated_at


@pytest.mark.unit_tests
def test_unsupported_pii_entities_to_exclude(client: GenaiEngineTestClientBase):
    disabled_checks = ["NOT_SUPPORTED", "WEATHER"]
    error = None
    try:
        status_code, rule = client.create_rule(
            "pii_exclude_PERSON",
            RuleType.PII_DATA,
            prompt_enabled=True,
            disabled_pii_entities=disabled_checks,
        )
    except Exception as e:
        error = e

    assert error is not None
    assert "disabled_pii_entities" in str(error)


@pytest.mark.unit_tests
def test_get_default_rules(
    create_default_rule: Rule,
    client: GenaiEngineTestClientBase,
):
    status_code, response = client.get_default_rules()
    assert status_code == 200
    assert response[0].name == create_default_rule.name
