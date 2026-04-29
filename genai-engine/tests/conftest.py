import os
import shutil
from typing import Generator

import pytest
from arthur_common.models.common_schemas import (
    ExamplesConfig,
    KeywordsConfig,
    PIIConfig,
    RegexConfig,
    ToxicityConfig,
)
from arthur_common.models.enums import PIIEntityTypes, RuleScope
from arthur_common.models.request_schemas import NewRuleRequest, NewTaskRequest

from dependencies import get_application_config
from repositories.inference_repository import InferenceRepository
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from schemas.internal_schemas import InferencePrompt, Rule, Task
from scorer.llm_client import LLMExecutor
from tests.clients.base_test_client import TEST_AUDIT_LOG_DIR, override_get_db_session


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
    os.environ["GENAI_ENGINE_THREAD_POOL_MAX_WORKERS"] = "1"


def create_rule_for_task(create_task: Task, rule_request: NewRuleRequest) -> Rule:
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    rules_repo = RuleRepository(db_session)
    metric_repo = MetricRepository(db_session)
    tasks_repo = TaskRepository(db_session, rules_repo, metric_repo, application_config)
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
    metric_repo = MetricRepository(db_session)
    tasks_repo = TaskRepository(db_session, rules_repo, metric_repo, application_config)
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


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_audit_logs():
    yield
    if os.path.exists(TEST_AUDIT_LOG_DIR):
        shutil.rmtree(TEST_AUDIT_LOG_DIR)


# ---------------------------------------------------------------------------
# Models service fakes
# ---------------------------------------------------------------------------

from clients.models_service_client import (  # noqa: E402
    ClaimFilterResponse,
    PIIResponse,
    PromptInjectionResponse,
    ToxicityResponse,
    _ClaimClassification,
    _PIIEntitySpan,
    _PromptInjectionChunk,
)


class FakeModelsServiceClient:
    """Drop-in stand-in for ModelsServiceClient.

    Each method returns a canned response (settable via the corresponding
    `*_response` attribute). Tests that exercise scorer wiring set the
    response shape and assert on the resulting RuleScore.
    """

    def __init__(self) -> None:
        self.prompt_injection_response = PromptInjectionResponse(result="Pass", chunks=[])
        self.toxicity_response = ToxicityResponse(
            result="Pass",
            toxicity_score=0.0,
            violation_type="benign",
            profanity_detected=False,
            max_toxicity_score=0.0,
            max_harmful_request_score=0.0,
        )
        self.pii_response = PIIResponse(result="Pass", entities=[])
        self.claim_filter_response = ClaimFilterResponse(classifications=[])

    # Recorded calls for assertions.
    last_call: tuple[str, dict] | None = None

    def prompt_injection(self, text: str) -> PromptInjectionResponse:
        self.last_call = ("prompt_injection", {"text": text})
        return self.prompt_injection_response

    def toxicity(self, text: str, threshold: float) -> ToxicityResponse:
        self.last_call = ("toxicity", {"text": text, "threshold": threshold})
        return self.toxicity_response

    def pii(
        self,
        text: str,
        disabled_entities: list[str] | None = None,
        allow_list: list[str] | None = None,
        confidence_threshold: float | None = None,
        use_v2: bool = True,
    ) -> PIIResponse:
        self.last_call = (
            "pii",
            {
                "text": text,
                "disabled_entities": disabled_entities or [],
                "allow_list": allow_list or [],
                "confidence_threshold": confidence_threshold,
                "use_v2": use_v2,
            },
        )
        return self.pii_response

    def claim_filter(self, texts: list[str]) -> ClaimFilterResponse:
        self.last_call = ("claim_filter", {"texts": texts})
        return self.claim_filter_response


@pytest.fixture
def fake_models_client() -> FakeModelsServiceClient:
    return FakeModelsServiceClient()


def make_pi_response(label: str, score: float = 0.99, text: str = "x") -> PromptInjectionResponse:
    """Helper for prompt-injection tests."""
    result = "Fail" if label == "INJECTION" else "Pass"
    return PromptInjectionResponse(
        result=result,
        chunks=[_PromptInjectionChunk(index=0, text=text, label=label, score=score)],
    )


def make_toxicity_response(
    *,
    result: str = "Pass",
    toxicity_score: float = 0.0,
    violation_type: str = "benign",
    profanity_detected: bool = False,
) -> ToxicityResponse:
    return ToxicityResponse(
        result=result,
        toxicity_score=toxicity_score,
        violation_type=violation_type,
        profanity_detected=profanity_detected,
        max_toxicity_score=toxicity_score if violation_type == "toxic_content" else 0.0,
        max_harmful_request_score=toxicity_score if violation_type == "harmful_request" else 0.0,
    )


def make_pii_response(*entities: tuple[str, str, float]) -> PIIResponse:
    """`entities` is a list of (entity_type, span, confidence)."""
    return PIIResponse(
        result="Fail" if entities else "Pass",
        entities=[
            _PIIEntitySpan(entity=e, span=s, confidence=c) for (e, s, c) in entities
        ],
    )


def make_claim_filter_response(*items: tuple[str, str, float]) -> ClaimFilterResponse:
    """`items` is a list of (text, label, confidence)."""
    return ClaimFilterResponse(
        classifications=[
            _ClaimClassification(text=t, label=l, confidence=c) for (t, l, c) in items
        ],
    )
