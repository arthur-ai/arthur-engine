import os
from typing import Generator

import pytest
from dependencies import get_application_config
from repositories.inference_repository import InferenceRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from schemas.common_schemas import (
    ExamplesConfig,
    KeywordsConfig,
    PIIConfig,
    RegexConfig,
    ToxicityConfig,
)
from schemas.enums import PIIEntityTypes, RuleScope
from schemas.internal_schemas import InferencePrompt, Rule, Task
from schemas.request_schemas import NewRuleRequest, NewTaskRequest
from scorer.llm_client import LLMExecutor
from tests.clients.base_test_client import override_get_db_session


def pytest_configure(config):
    config.addinivalue_line("markers", "unit_tests: marks tests as unit tests")
    config.addinivalue_line(
        "markers",
        "api_key_tests: mark a test as testing api key actions",
    )
    config.addinivalue_line(
        "markers",
        "aws_live: mark a test as running against a live environment. AWS_BUCKET_NAME must be supplied as an environment variable",
    )
    config.addinivalue_line(
        "markers",
        "azure_live: mark a test as running against a live environment. AZURE_STORAGE_CONTAINER_NAME and AZURE_STORAGE_CONNECTION_STRING must be supplied as a environment variables",
    )
    config.addinivalue_line(
        "markers",
        "integration_tests: mark a test as running an integration test. These will tend to replicate user flows and minimize the amount of junk data created",
    )
    config.addinivalue_line(
        "markers",
        "unit_tests: mark a test as part of the unit tests suite. These should run locally with no outside configuration required. Should also be entirely self contained (no external dependencies)",
    )
    config.addinivalue_line(
        "markers",
        "skip_auto_api_key_create: mark a test as opting out of api key creation and deletion pre and post steps",
    )


@pytest.fixture(autouse=True)
def set_env_vars():
    os.environ["NEW_RELIC_ENABLED"] = "false"


def create_rule_for_task(create_task: Task, rule_request: NewRuleRequest) -> Rule:
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    rules_repo = RuleRepository(db_session)
    tasks_repo = TaskRepository(db_session, rules_repo, application_config)
    new_rule = rules_repo.create_rule(
        Rule._from_request_model(rule_request, scope=RuleScope.TASK),
    )
    tasks_repo.link_rule_to_task(create_task.id, new_rule.id, new_rule.type)

    return new_rule


def create_prompt_in_db(
    inference_repository: InferenceRepository,
    task_id: str | None = None,
) -> InferencePrompt:
    prompt = inference_repository.save_prompt(
        prompt=f"Is this the real life number?",
        prompt_rule_results=[],
        conversation_id=f"dummy_conversation_id",
        user_id="genai_engine_user",
        task_id=task_id,
    )

    return prompt


@pytest.fixture
def create_task() -> Generator[Task, None, None]:
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    request = NewTaskRequest(name="dummy_task_name")
    rules_repo = RuleRepository(db_session)
    tasks_repo = TaskRepository(db_session, rules_repo, application_config)
    task = Task._from_request_model(request)
    task = tasks_repo.create_task(task)

    yield task

    if task.rule_links:
        for rule_link in task.rule_links:
            tasks_repo.delete_rule_link(task_id=task.id, rule_id=rule_link.rule_id)
    tasks_repo.delete_task(task_id=task.id)


@pytest.fixture
def create_prompt_inference_with_task(
    create_task: Task,
) -> Generator[tuple[Task, InferencePrompt], None, None]:
    db_session = override_get_db_session()
    inference_repository = InferenceRepository(
        db_session=db_session,
    )

    prompt = create_prompt_in_db(inference_repository, create_task.id)

    yield create_task, prompt

    inference_repository.delete_inference(inference_id=prompt.inference_id)


@pytest.fixture
def create_rule_for_task_hallucination_v2(
    create_task: Task,
) -> Generator[Rule, None, None]:
    request = NewRuleRequest(
        name="dummy_hallucination_v2_rule_name",
        type="ModelHallucinationRuleV2",
        apply_to_prompt=False,
        apply_to_response=True,
    )

    rule = create_rule_for_task(create_task, request)

    yield rule

    db_session = override_get_db_session()
    rules_repo = RuleRepository(db_session)

    rules_repo.delete_rule(rule_id=rule.id)


@pytest.fixture
def create_rule_for_task_sensitive_data(
    create_task: Task,
) -> Generator[Rule, None, None]:
    request = NewRuleRequest(
        name="dummy_sensitive_data_rule_name",
        type="ModelSensitiveDataRule",
        apply_to_prompt=True,
        apply_to_response=False,
        config=ExamplesConfig(
            examples=[
                {
                    "example": "John has O negative blood group",
                    "result": True,
                },
                {
                    "example": "Most of the people have A positive blood group",
                    "result": False,
                },
            ],
            hint="specific individual's blood types",
        ),
    )

    rule = create_rule_for_task(create_task, request)

    yield rule

    db_session = override_get_db_session()
    rules_repo = RuleRepository(db_session)

    rules_repo.delete_rule(rule_id=rule.id)


@pytest.fixture
def create_rule_for_task_regex(create_task: Task) -> Generator[Rule, None, None]:
    request = NewRuleRequest(
        name="dummy_regex_rule_name",
        type="RegexRule",
        apply_to_prompt=True,
        apply_to_response=True,
        config=RegexConfig(
            regex_patterns=[
                "\\d{3}-\\d{2}-\\d{4}",
                "\\d{5}-\\d{6}-\\d{7}",
            ],
        ),
    )

    rule = create_rule_for_task(create_task, request)

    yield rule

    db_session = override_get_db_session()
    rules_repo = RuleRepository(db_session)

    rules_repo.delete_rule(rule_id=rule.id)


@pytest.fixture
def create_rule_for_task_keywords(create_task: Task) -> Generator[Rule, None, None]:
    request = NewRuleRequest(
        name="dummy_keywords_rule_name",
        type="KeywordRule",
        apply_to_prompt=True,
        apply_to_response=True,
        config=KeywordsConfig(
            keywords=["confidential", "secret", "private"],
            case_sensitive=False,
        ),
    )

    rule = create_rule_for_task(create_task, request)

    yield rule

    db_session = override_get_db_session()
    rules_repo = RuleRepository(db_session)

    rules_repo.delete_rule(rule_id=rule.id)


@pytest.fixture
def create_rule_for_task_prompt_injection(
    create_task: Task,
) -> Generator[Rule, None, None]:
    request = NewRuleRequest(
        name="dummy_prompt_injection_rule_name",
        type="PromptInjectionRule",
        apply_to_prompt=True,
        apply_to_response=False,
    )

    rule = create_rule_for_task(create_task, request)

    yield rule

    db_session = override_get_db_session()
    rules_repo = RuleRepository(db_session)

    rules_repo.delete_rule(rule_id=rule.id)


@pytest.fixture
def create_rule_for_task_pii(create_task: Task) -> Generator[Rule, None, None]:
    request = NewRuleRequest(
        name="dummy_pii_rule_name",
        type="PIIDataRule",
        apply_to_prompt=True,
        apply_to_response=True,
        config=PIIConfig(
            disabled_pii_entities=[
                PIIEntityTypes.EMAIL_ADDRESS,
                PIIEntityTypes.PHONE_NUMBER,
            ],
            confidence_threshold="0.5",
            allow_list=["arthur.ai", "Arthur"],
        ),
    )

    rule = create_rule_for_task(create_task, request)

    yield rule

    db_session = override_get_db_session()
    rules_repo = RuleRepository(db_session)

    rules_repo.delete_rule(rule_id=rule.id)


@pytest.fixture
def create_rule_for_task_toxicity(create_task: Task) -> Generator[Rule, None, None]:
    request = NewRuleRequest(
        name="dummy_toxicity_rule_name",
        type="ToxicityRule",
        apply_to_prompt=True,
        apply_to_response=True,
        config=ToxicityConfig(threshold=0.7),
    )

    rule = create_rule_for_task(create_task, request)

    yield rule

    db_session = override_get_db_session()
    rules_repo = RuleRepository(db_session)

    rules_repo.delete_rule(rule_id=rule.id)


@pytest.fixture
def openai_executor(
    request: pytest.FixtureRequest,
) -> Generator[LLMExecutor, None, None]:
    llm_config = request.param
    llm_client = LLMExecutor(llm_config)
    yield llm_client
