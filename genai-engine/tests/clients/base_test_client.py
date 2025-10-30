import os
import random
import urllib
from datetime import datetime
from typing import Any

import httpx
from arthur_common.models.common_schemas import (
    ExamplesConfig,
    KeywordsConfig,
    PIIConfig,
    RegexConfig,
    ToxicityConfig,
    UserPermission,
)
from arthur_common.models.enums import (
    InferenceFeedbackTarget,
    PaginationSortMethod,
    RuleResultEnum,
    RuleScope,
    RuleType,
    TokenUsageScope,
)
from arthur_common.models.request_schemas import (
    ChatDefaultTaskRequest,
    CreateUserRequest,
    FeedbackRequest,
    NewTaskRequest,
    PasswordResetRequest,
    SearchRulesRequest,
    SearchTasksRequest,
)
from arthur_common.models.response_schemas import (
    ApiKeyResponse,
    ChatDefaultTaskResponse,
    ChatDocumentContext,
    ChatResponse,
    ExternalDocument,
    FileUploadResult,
    QueryFeedbackResponse,
    QueryInferencesResponse,
    QuerySpansResponse,
    QueryTracesWithMetricsResponse,
    RuleResponse,
    SearchRulesResponse,
    SearchTasksResponse,
    SpanWithMetricsResponse,
    TaskResponse,
    TokenUsageResponse,
    TraceResponse,
    UserResponse,
    ValidationResult,
)
from pydantic import TypeAdapter
from sqlalchemy.orm import sessionmaker

from config.database_config import DatabaseConfig
from schemas.enums import (
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
    RagProviderEnum,
)
from schemas.request_schemas import (
    ApiKeyRagAuthenticationConfigRequest,
    ApiKeyRagAuthenticationConfigUpdateRequest,
    DatasetUpdateRequest,
    NewDatasetRequest,
    NewDatasetVersionRequest,
    NewDatasetVersionRowRequest,
    NewDatasetVersionUpdateRowRequest,
    RagKeywordSearchSettingRequest,
    RagProviderConfigurationRequest,
    RagProviderConfigurationUpdateRequest,
    RagVectorSimilarityTextSearchSettingRequest,
    WeaviateKeywordSearchSettingsRequest,
    WeaviateVectorSimilarityTextSearchSettingsRequest,
)
from schemas.response_schemas import (
    ConnectionCheckResult,
    DatasetResponse,
    DatasetVersionResponse,
    ListDatasetVersionsResponse,
    RagProviderConfigurationResponse,
    RagProviderQueryResponse,
    SearchDatasetsResponse,
    SearchRagProviderConfigurationsResponse,
    SessionListResponse,
    SessionTracesResponse,
    SpanListResponse,
    TraceListResponse,
    TraceUserListResponse,
    TraceUserMetadataResponse,
)
from tests.constants import (
    DEFAULT_EXAMPLES,
    DEFAULT_KEYWORDS,
    DEFAULT_REGEX,
    EXAMPLE_PROMPTS,
    EXAMPLE_RESPONSES,
)
from tests.mocks.mock_jwk_client import MockJWKClient
from tests.mocks.mock_keycloak_client import MockAuthClient
from tests.mocks.mock_oauth_client import MockAuthClient
from tests.mocks.mock_scorer_client import MockScorerClient
from utils import constants
from utils.utils import get_env_var

MASTER_API_KEY = (
    "Tests" if "REMOTE_TEST_KEY" not in os.environ else os.environ["REMOTE_TEST_KEY"]
)
os.environ[constants.GENAI_ENGINE_ADMIN_KEY_ENV_VAR] = MASTER_API_KEY
os.environ[constants.GENAI_ENGINE_ENVIRONMENT_ENV_VAR] = "local"
os.environ[constants.GENAI_ENGINE_APP_SECRET_KEY_ENV_VAR] = "abcdef"
os.environ[constants.GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS_ENV_VAR] = "60"
os.environ[constants.GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD_ENV_VAR] = "5000"
os.environ[constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR] = "http://localhost"
os.environ[constants.ALLOW_ADMIN_KEY_GENERAL_ACCESS_ENV_VAR] = "enabled"
os.environ[constants.GENAI_ENGINE_CHAT_ENABLED_ENV_VAR] = "enabled"
os.environ[constants.TELEMETRY_ENABLED_ENV_VAR] = "False"

MASTER_KEY_AUTHORIZED_HEADERS = {"Authorization": "Bearer %s" % MASTER_API_KEY}
AUTHORIZED_CHAT_HEADERS = {"Authorization": "Bearer %s" % "user_0"}
DATABASE_ENGINE = None


def override_get_scorer_client():
    return MockScorerClient()


def override_get_jwk_client():
    return MockJWKClient()


def override_get_keycloak_client():
    return MockAuthClient()


def override_get_db_session():
    global DATABASE_ENGINE
    if DATABASE_ENGINE is None:
        DATABASE_ENGINE = get_db_engine(DatabaseConfig(TEST_DATABASE=True))

    session = sessionmaker(DATABASE_ENGINE)
    return session()


def override_oauth_client():
    return MockAuthClient()


# Import app after env vars are set
from dependencies import (
    get_db_engine,
    get_db_session,
    get_jwk_client,
    get_keycloak_client,
    get_oauth_client,
    get_scorer_client,
)
from server import get_test_app

app = get_test_app()

app.dependency_overrides[get_db_session] = override_get_db_session
app.dependency_overrides[get_scorer_client] = override_get_scorer_client
app.dependency_overrides[get_jwk_client] = override_get_jwk_client
app.dependency_overrides[get_oauth_client] = override_oauth_client
app.dependency_overrides[get_keycloak_client] = override_get_keycloak_client


class GenaiEngineTestClientBase(httpx.Client):
    def __init__(
        self,
        client: httpx.Client,
        authorized_chat_headers: dict = None,
        create_user_key: bool = True,
        create_org_admin: bool = True,
        auth_server_url: str = "",
    ):
        self.base_client: httpx.Client = client
        self.auth_server_url: str = auth_server_url
        self.authorized_chat_headers: dict = authorized_chat_headers
        self.authorized_user_api_key_headers: dict = None
        self.authorized_org_admin_api_key_headers: dict = {
            "Authorization": "Bearer admin_0",
        }

        if create_user_key:
            # Clear existing keys, create a new one to avoid hitting user key limits
            self.clear_existing_user_keys()
            sc, user_key = self.create_api_key(
                description="TestClient",
                roles=[constants.TASK_ADMIN],
            )
            assert sc == 200
            self.authorized_user_api_key_headers = {
                "Authorization": "Bearer %s" % user_key.key,
            }
        if create_org_admin:
            sc, user_key = self.create_api_key(
                description="OrgAdminClient",
                roles=[
                    constants.ORG_ADMIN,
                ],
            )
            assert sc == 200
            self.authorized_org_admin_api_key_headers = {
                "Authorization": f"Bearer {user_key.key}",
            }

    def get_loggedin_user_headers(self, user_name: str, password: str) -> dict:
        data = {
            "username": user_name,
            "client_id": "arthur-genai-engine",
            "grant_type": "password",
            "client_secret": get_env_var(
                constants.GENAI_ENGINE_AUTH_CLIENT_SECRET_ENV_VAR,
            ),
            "password": password,
        }
        token_resp = self.base_client.post(
            f"{self.auth_server_url}/realms/genai_engine/protocol/openid-connect/token",
            data=data,
        )
        if token_resp.status_code != 200:
            raise AttributeError("Chat token retrival failed")

        return {"Authorization": "Bearer %s" % token_resp.json()["access_token"]}

    def clear_existing_user_keys(self):
        _, keys = self.get_api_keys()
        for key in keys:
            sc = self.deactivate_api_key(key)
            assert sc == 204

    def create_api_key(
        self,
        description: str | None = None,
        roles: list[str] = [constants.TASK_ADMIN],
    ) -> tuple[int, ApiKeyResponse]:
        request = {
            "description": description,
            "roles": roles,
        }
        path = "/auth/api_keys/"
        response = self.base_client.post(
            path,
            json=request,
            headers=MASTER_KEY_AUTHORIZED_HEADERS,
        )
        log_response(response)

        return (
            response.status_code,
            (
                ApiKeyResponse.model_validate(response.json())
                if response.status_code == 200
                else None
            ),
        )

    def deactivate_api_key(self, api_key: ApiKeyResponse) -> int:
        path = f"/auth/api_keys/deactivate/{api_key.id}"
        response = self.base_client.delete(path, headers=MASTER_KEY_AUTHORIZED_HEADERS)
        log_response(response)

        return response.status_code

    def get_api_keys(self) -> tuple[int, list[ApiKeyResponse]]:
        path = "/auth/api_keys/"
        response = self.base_client.get(path, headers=MASTER_KEY_AUTHORIZED_HEADERS)
        log_response(response)

        adapter = TypeAdapter(list[ApiKeyResponse])

        return (
            response.status_code,
            (
                adapter.validate_python(response.json())
                if response.status_code == 200
                else None
            ),
        )

    def get_api_key_by_id(self, api_key_id: str) -> tuple[int, list[ApiKeyResponse]]:
        path = f"/auth/api_keys/{api_key_id}"
        response = self.base_client.get(path, headers=MASTER_KEY_AUTHORIZED_HEADERS)
        log_response(response)

        return (
            response.status_code,
            (
                ApiKeyResponse.model_validate(response.json())
                if response.status_code == 200
                else None
            ),
        )

    def get_task(self, task_id: str) -> tuple[int, TaskResponse]:
        path = f"api/v2/tasks/{task_id}"
        resp = self.base_client.get(path, headers=self.authorized_user_api_key_headers)
        log_response(resp)

        return (
            resp.status_code,
            (
                TaskResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def search_tasks(
        self,
        sort: PaginationSortMethod = None,
        page: int = None,
        page_size: int = None,
        task_ids: list[str] = None,
        task_name: str = None,
        is_agentic: bool = None,
    ) -> tuple[int, SearchTasksResponse]:
        path = "api/v2/tasks/search?"
        params = get_base_pagination_parameters(
            sort=sort,
            page=page,
            page_size=page_size,
        )
        body = SearchTasksRequest()
        if task_ids:
            body.task_ids = task_ids
        if task_name:
            body.task_name = task_name
        if is_agentic is not None:
            body.is_agentic = is_agentic

        resp = self.base_client.post(
            "{}{}".format(path, urllib.parse.urlencode(params, doseq=True)),
            json=body.model_dump(),
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                SearchTasksResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def search_rules(
        self,
        sort: PaginationSortMethod = None,
        page: int = None,
        page_size: int = None,
        rule_ids: list[str] = None,
        prompt_enabled: bool = None,
        response_enabled: bool = None,
        rule_scopes: list[RuleScope] = None,
        rule_types: list[RuleType] = None,
    ) -> tuple[int, SearchRulesResponse]:
        path = "api/v2/rules/search?"
        params = get_base_pagination_parameters(
            sort=sort,
            page=page,
            page_size=page_size,
        )
        body = SearchRulesRequest()
        if rule_ids:
            body.rule_ids = rule_ids
        if prompt_enabled:
            body.prompt_enabled = prompt_enabled
        if response_enabled:
            body.response_enabled = response_enabled
        if rule_scopes:
            body.rule_scopes = rule_scopes
        if rule_types:
            body.rule_types = rule_types

        resp = self.base_client.post(
            "{}{}".format(path, urllib.parse.urlencode(params, doseq=True)),
            json=body.model_dump(),
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                SearchRulesResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def create_task(
        self,
        name: str = None,
        is_agentic: bool = False,
        empty_rules: bool = False,
        user_id: str = None,
    ) -> tuple[int, TaskResponse]:
        name = name if name else str(random.random())
        request = NewTaskRequest(name=name, is_agentic=is_agentic)

        resp = self.base_client.post(
            "/api/v2/tasks",
            json=request.model_dump(),
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        if resp.status_code == 200 and empty_rules:
            task = TaskResponse.model_validate(resp.json())
            _, task = self.get_task(task.id)
            rule_ids = [r.id for r in task.rules]
            for id in rule_ids:
                s, _ = self.patch_rule(task.id, id, False)
                assert s == 200

        return (
            resp.status_code,
            (
                TaskResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def create_task_metric(
        self,
        task_id: str,
        metric_type: str = "QueryRelevance",
        metric_name: str = "Test Metric",
        metric_metadata: str = "Test metric for testing",
        config: dict = None,
        user_id: str = None,
    ) -> tuple[int, dict | None]:
        """Create a metric for a task."""
        request = {
            "type": metric_type,
            "name": metric_name,
            "metric_metadata": metric_metadata,
            "config": config,
        }

        resp = self.base_client.post(
            f"/api/v2/tasks/{task_id}/metrics",
            json=request,
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            resp.json() if resp.status_code == 201 else None,
        )

    def update_task_metric(
        self,
        task_id: str,
        metric_id: str,
        enabled: bool,
        user_id: str = None,
    ) -> tuple[int, dict | None]:
        """Update a task metric's enabled status."""
        request = {"enabled": enabled}

        resp = self.base_client.patch(
            f"/api/v2/tasks/{task_id}/metrics/{metric_id}",
            json=request,
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            resp.json() if resp.status_code == 200 else None,
        )

    def archive_task_metric(
        self,
        task_id: str,
        metric_id: str,
        user_id: str = None,
    ) -> tuple[int, str | None]:
        """Archive a task metric."""
        resp = self.base_client.delete(
            f"/api/v2/tasks/{task_id}/metrics/{metric_id}",
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            resp.text if resp.status_code != 204 else None,
        )

    def create_rule(
        self,
        name: str,
        rule_type: RuleType,
        regex_patterns=DEFAULT_REGEX,
        keywords=DEFAULT_KEYWORDS,
        task_id=None,
        examples=DEFAULT_EXAMPLES,
        prompt_enabled=None,
        response_enabled=None,
        toxicity_threshold=None,
        pii_confidence_threshold=None,
        disabled_pii_entities=None,
        allow_list=None,
        skip_config=False,
        use_org_admin: bool = True,
    ) -> tuple[int, RuleResponse]:
        if not rule_type in RuleType:
            raise ValueError(f"Invalid rule type: {rule_type}")

        rule = {
            "name": name,
            "type": rule_type,
        }

        if rule_type == RuleType.REGEX:
            rule["apply_to_prompt"] = bool(prompt_enabled) or True
            rule["apply_to_response"] = bool(response_enabled) or True
            if not skip_config:
                rule["config"] = RegexConfig(regex_patterns=regex_patterns).model_dump()
        elif rule_type == RuleType.KEYWORD:
            rule["apply_to_prompt"] = bool(prompt_enabled) or True
            rule["apply_to_response"] = bool(response_enabled) or True
            if not skip_config:
                rule["config"] = KeywordsConfig(keywords=keywords).model_dump()
        elif rule_type == RuleType.MODEL_SENSITIVE_DATA:
            rule["apply_to_prompt"] = bool(prompt_enabled) or True
            rule["apply_to_response"] = bool(response_enabled) or False
            if not skip_config:
                rule["config"] = ExamplesConfig(examples=examples).model_dump()
        elif rule_type == RuleType.MODEL_HALLUCINATION_V2:
            rule["apply_to_prompt"] = bool(prompt_enabled) or False
            rule["apply_to_response"] = bool(response_enabled) or True
        elif rule_type == RuleType.PII_DATA:
            rule["apply_to_prompt"] = bool(prompt_enabled) or True
            rule["apply_to_response"] = bool(response_enabled) or True
            if not skip_config:
                rule["config"] = PIIConfig(
                    confidence_threshold=pii_confidence_threshold,
                    disabled_pii_entities=disabled_pii_entities,
                    allow_list=allow_list,
                ).model_dump()
        elif rule_type == RuleType.PROMPT_INJECTION:
            rule["apply_to_prompt"] = True
            rule["apply_to_response"] = False
            if not skip_config:
                rule["config"] = None
        elif rule_type == RuleType.TOXICITY:
            rule["apply_to_prompt"] = bool(prompt_enabled) or True
            rule["apply_to_response"] = bool(response_enabled) or True
            if not skip_config:
                rule["config"] = ToxicityConfig(
                    threshold=toxicity_threshold,
                ).model_dump()

        headers_with_authorization = (self.authorized_user_api_key_headers,)
        if use_org_admin:
            headers_with_authorization = self.authorized_org_admin_api_key_headers
        if not task_id:
            url = "/api/v2/default_rules"
        else:
            url = f"/api/v2/tasks/{task_id}/rules"

        resp = self.base_client.post(
            url,
            json=rule,
            headers=headers_with_authorization,
        )
        log_response(resp)
        return (
            resp.status_code,
            (
                RuleResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.json()
            ),
        )

    def patch_rule(
        self,
        task_id: str,
        rule_id: str,
        enabled: bool,
    ) -> tuple[int, TaskResponse]:
        resp = self.base_client.patch(
            f"/api/v2/tasks/{task_id}/rules/{rule_id}",
            json={"enabled": enabled},
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                TaskResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def query_inferences(
        self,
        sort=None,
        page=None,
        task_ids: list[str] = None,
        task_name: str | None = None,
        conversation_id=None,
        inference_id: str | None = None,
        user_id: str | None = None,
        page_size=None,
        start_time=None,
        end_time=None,
        rule_types: list[RuleType] = None,
        rule_statuses: list[RuleResultEnum] = None,
        prompt_results: list[RuleResultEnum] = None,
        response_results: list[RuleResultEnum] = None,
        include_count: bool = True,
    ) -> tuple[int, QueryInferencesResponse]:
        params = {"include_count": include_count}

        if sort is not None:
            params["sort"] = sort
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if task_ids is not None:
            params["task_ids"] = task_ids
        if task_name:
            params["task_name"] = task_name
        if conversation_id is not None:
            params["conversation_id"] = conversation_id
        if inference_id is not None:
            params["inference_id"] = inference_id
        if user_id is not None:
            params["user_id"] = user_id
        if start_time is not None:
            params["start_time"] = str(start_time)
        if end_time is not None:
            params["end_time"] = str(end_time)
        if rule_types:
            params["rule_types"] = rule_types
        if rule_statuses:
            params["rule_statuses"] = rule_statuses
        if prompt_results:
            params["prompt_statuses"] = prompt_results
        if response_results:
            params["response_statuses"] = response_results

        resp = self.base_client.get(
            f"api/v2/inferences/query?{urllib.parse.urlencode(params, doseq=True)}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                QueryInferencesResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def query_all_inferences(self, sort=None) -> QueryInferencesResponse:
        page_size, page = 250, 0
        total_query_resp = QueryInferencesResponse(count=0, inferences=[])
        count = None
        while True:
            status_code, query_resp = self.query_inferences(
                sort=sort,
                page=page,
                page_size=page_size,
            )
            assert status_code == 200
            total_query_resp.inferences.extend(query_resp.inferences)
            total_query_resp.count = query_resp.count
            if not count:
                count = query_resp.count
            else:
                assert count == query_resp.count

            page += 1
            if len(query_resp.inferences) != page_size:
                break

        return total_query_resp

    def create_prompt(
        self,
        prompt: str = None,
        task_id: str = None,
        conversation_id: str = None,
        user_id: str = None,
    ) -> tuple[int, ValidationResult]:
        uri = "/api/v2/validate_prompt"
        if task_id != None:
            uri = f"/api/v2/tasks/{task_id}/validate_prompt"
        if prompt is None:
            prompt = random.choice(EXAMPLE_PROMPTS)

        request_body = {
            "prompt": prompt,
            "conversation_id": conversation_id,
            "user_id": user_id,
        }

        resp = self.base_client.post(
            url=uri,
            json=request_body,
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                ValidationResult.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def create_response(
        self,
        inference_id: str,
        response: str = None,
        task_id: str = None,
        context: str = None,
        model_name: str = None,
    ) -> tuple[int, ValidationResult]:
        uri = "/api/v2/validate_response/"
        if task_id != None:
            uri = f"/api/v2/tasks/{task_id}/validate_response/"

        body = {"response": response if response else random.choice(EXAMPLE_RESPONSES)}
        if context:
            body["context"] = context
        if model_name:
            body["model_name"] = model_name
        resp = self.base_client.post(
            uri + inference_id,
            json=body,
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                ValidationResult.model_validate(resp.json())
                if resp.status_code == 200
                else resp.json()
            ),
        )

    def send_chat_feedback(
        self,
        inference_id: str,
        target: str,
        score: int,
        reason: str,
    ) -> int:
        request = FeedbackRequest(target=target, score=score, reason=reason)
        resp = self.base_client.post(
            f"/api/chat/feedback/{inference_id}",
            json=request.model_dump(),
            headers=self.authorized_chat_headers,
        )

        log_response(resp)

        return resp.status_code

    def delete_default_rule(self, rule_id: str) -> int:
        path = f"api/v2/default_rules/{rule_id}"
        resp = self.base_client.delete(
            path,
            headers=self.authorized_org_admin_api_key_headers,
        )

        log_response(resp)

        return resp.status_code

    def delete_task_rule(self, task_id: str, rule_id: str) -> int:
        resp = self.base_client.delete(
            f"/api/v2/tasks/{task_id}/rules/{rule_id}",
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return resp.status_code

    def update_configs(self, application_configs: dict, headers: dict | None = None):
        if not headers:
            headers = self.authorized_user_api_key_headers
        uri = "/api/v2/configuration"
        resp = self.base_client.post(
            uri,
            json=application_configs,
            headers=headers,
        )
        log_response(resp)
        return resp

    def get_configs(self, headers: dict | None = None):
        if not headers:
            headers = self.authorized_user_api_key_headers
        uri = "/api/v2/configuration"
        resp = self.base_client.get(
            uri,
            headers=headers,
        )
        log_response(resp)
        return resp

    def upload_file(
        self,
        file_path,
        file_name,
        content_type,
        headers=None,
        is_global=False,
    ) -> tuple[int, FileUploadResult]:
        if headers is None:
            headers = self.authorized_chat_headers
        with open(file_path, "rb") as f:
            path = "/api/chat/files?"
            params = {"is_global": is_global}

            response = self.base_client.post(
                "{}{}".format(path, urllib.parse.urlencode(params)),
                files={"file": (file_name, f, content_type)},
                headers=headers,
            )
            log_response(response)
            return (
                response.status_code,
                (
                    FileUploadResult.model_validate(response.json())
                    if response.status_code == 200
                    else None
                ),
            )

    def delete_file(self, file_id: str, headers=None) -> int:
        resp = self.base_client.delete(
            "/api/chat/files/%s?" % file_id,
            headers=self.authorized_chat_headers if headers is None else headers,
        )

        log_response(resp)

        return resp.status_code

    def get_files(self, headers=None) -> tuple[int, list[ExternalDocument]]:
        if headers is None:
            headers = self.authorized_chat_headers
        path = "/api/chat/files?"
        params = {}

        response = self.base_client.get(
            "{}{}".format(path, urllib.parse.urlencode(params)),
            headers=headers,
        )
        log_response(response)

        adapter = TypeAdapter(list[ExternalDocument])

        return (
            response.status_code,
            (
                adapter.validate_python(response.json())
                if response.status_code == 200
                else None
            ),
        )

    def delete_task(self, task_id: str) -> int:
        resp = self.base_client.delete(
            f"/api/v2/tasks/{task_id}",
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return resp.status_code

    def create_dataset(
        self,
        name: str,
        description: str = None,
        metadata: dict = None,
    ) -> tuple[int, DatasetResponse]:
        request = NewDatasetRequest(
            name=name,
            description=description,
            metadata=metadata,
        )

        resp = self.base_client.post(
            "/api/v2/datasets",
            json=request.model_dump(),
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                DatasetResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def get_dataset(self, dataset_id: str) -> tuple[int, DatasetResponse]:
        resp = self.base_client.get(
            f"/api/v2/datasets/{dataset_id}",
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                DatasetResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def update_dataset(
        self,
        dataset_id: str,
        name: str = None,
        description: str = None,
        metadata: dict = None,
    ) -> tuple[int, DatasetResponse]:
        request = DatasetUpdateRequest(
            name=name,
            description=description,
            metadata=metadata,
        )

        resp = self.base_client.patch(
            f"/api/v2/datasets/{dataset_id}",
            json=request.model_dump(),
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                DatasetResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def delete_dataset(self, dataset_id: str) -> int:
        resp = self.base_client.delete(
            f"/api/v2/datasets/{dataset_id}",
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return resp.status_code

    def search_datasets(
        self,
        sort: PaginationSortMethod = None,
        page: int = None,
        page_size: int = None,
        dataset_ids: list[str] = None,
        dataset_name: str = None,
    ) -> tuple[int, SearchDatasetsResponse]:
        """Search datasets with optional filters and pagination."""
        path = "api/v2/datasets/search?"
        params = get_base_pagination_parameters(
            sort=sort,
            page=page,
            page_size=page_size,
        )
        if dataset_ids:
            params["dataset_ids"] = dataset_ids
        if dataset_name:
            params["dataset_name"] = dataset_name

        resp = self.base_client.get(
            "{}{}".format(path, urllib.parse.urlencode(params, doseq=True)),
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                SearchDatasetsResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def send_chat(
        self,
        user_prompt: str,
        conversation_id: str,
        file_ids: list[str],
    ) -> tuple[int, ChatResponse]:
        request = {
            "user_prompt": user_prompt,
            "conversation_id": conversation_id,
            "file_ids": file_ids,
        }

        resp = self.base_client.post(
            "/api/chat/",
            json=request,
            headers=self.authorized_chat_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                ChatResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def get_inference_document_context(
        self,
        inference_id: str,
    ) -> tuple[int, list[ChatDocumentContext]]:
        resp = self.base_client.get(
            f"/api/chat/context/{inference_id}",
            headers=self.authorized_chat_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                [ChatDocumentContext.model_validate(i) for i in resp.json()]
                if resp.status_code == 200
                else None
            ),
        )

    def get_token_usage(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        group_by: list[TokenUsageScope] = None,
        headers: dict[str, str] = MASTER_KEY_AUTHORIZED_HEADERS,
    ) -> tuple[int, list[TokenUsageResponse]]:
        path = "api/v2/usage/tokens?"
        params = {}
        if start_time:
            params["start_time"] = str(start_time)
        if end_time:
            params["end_time"] = str(end_time)
        if group_by:
            params["group_by"] = group_by

        response = self.base_client.get(
            "{}{}".format(path, urllib.parse.urlencode(params, doseq=True)),
            headers=headers,
        )
        log_response(response)

        entries = []
        if response.status_code == 200:
            for entry in response.json():
                entries.append(TokenUsageResponse.model_validate(entry))

        return response.status_code, entries

    def create_user(
        self,
        user_email: str,
        password: str,
        roles: list[str],
        firstName: str,
        lastName: str,
        temporary: bool = True,
    ) -> int:
        path = "users"
        request_body = CreateUserRequest(
            email=user_email,
            password=password,
            temporary=temporary,
            roles=roles,
            firstName=firstName,
            lastName=lastName,
        )
        resp = self.base_client.post(
            path,
            headers=self.authorized_org_admin_api_key_headers,
            data=request_body.model_dump_json(),
        )
        log_response(resp)

        return resp.status_code

    def get_users(self, search_string: str) -> tuple[int, list[UserResponse]]:
        path = "users?"
        params = {}
        if search_string:
            params["search_string"] = str(search_string)
        resp = self.base_client.get(
            "{}{}".format(path, urllib.parse.urlencode(params, doseq=True)),
            headers=self.authorized_org_admin_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                [UserResponse.model_validate(i) for i in resp.json()]
                if resp.status_code == 200
                else None
            ),
        )

    def delete_user(self, user_id: str) -> int:
        path = f"users/{user_id}"
        resp = self.base_client.delete(
            path,
            headers=self.authorized_org_admin_api_key_headers,
        )
        log_response(resp)

        return resp.status_code

    def check_user_permission(
        self,
        permission: UserPermission,
        user_headers: dict,
    ) -> int:
        path = "users/permissions/check?"
        params = {"action": permission.action, "resource": permission.resource}

        resp = self.base_client.get(
            "{}{}".format(path, urllib.parse.urlencode(params)),
            headers=user_headers,
        )
        log_response(resp)

        return resp.status_code

    def reset_password(
        self,
        user_id: str,
        new_password: str,
    ) -> tuple[int, dict[str, str] | None]:
        path = f"users/{user_id}/reset_password"
        password_request = PasswordResetRequest(password=new_password)

        resp = self.base_client.post(
            path,
            data=password_request.model_dump_json(),
            headers=self.authorized_chat_headers,
        )

        return resp.status_code, resp.json()

    def post_feedback(
        self,
        target: InferenceFeedbackTarget,
        score: int,
        reason: str | None,
        user_id: str | None,
        inference_id: str,
    ) -> tuple[int, dict[str, Any] | None]:
        path = f"api/v2/feedback/{inference_id}"
        params = FeedbackRequest(
            target=target,
            score=score,
            reason=reason,
            user_id=user_id,
        )
        resp = self.base_client.post(
            path,
            json=params.model_dump(),
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return resp.status_code, resp.json()

    def query_feedback(
        self,
        sort: PaginationSortMethod | None = None,
        page: int | None = None,
        page_size: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        feedback_id: str | list[str] | None = None,
        inference_id: str | list[str] | None = None,
        target: str | list[str] | None = None,
        score: int | list[int] | None = None,
        feedback_user_id: str | None = None,
        conversation_id: str | list[str] | None = None,
        task_id: str | list[str] | None = None,
        inference_user_id: str | None = None,
    ) -> tuple[int, QueryFeedbackResponse | None]:
        path = f"api/v2/feedback/query?"
        params = {}

        if sort is not None:
            params["sort"] = sort
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if start_time is not None:
            params["start_time"] = str(start_time)
        if end_time is not None:
            params["end_time"] = str(end_time)
        if feedback_id is not None:
            params["feedback_id"] = feedback_id
        if inference_id is not None:
            params["inference_id"] = inference_id
        if target is not None:
            params["target"] = target
        if score is not None:
            params["score"] = score
        if feedback_user_id is not None:
            params["feedback_user_id"] = feedback_user_id
        if conversation_id is not None:
            params["conversation_id"] = conversation_id
        if task_id is not None:
            params["task_id"] = task_id
        if feedback_user_id is not None:
            params["feedback_user_id"] = feedback_user_id
        if inference_user_id is not None:
            params["inference_user_id"] = inference_user_id

        resp = self.base_client.get(
            f"{path}{urllib.parse.urlencode(params, doseq=True)}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                QueryFeedbackResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def get_conversations(self, page: int = 1, size: int = 50) -> tuple[int, dict]:
        resp = self.base_client.get(
            f"/api/chat/conversations?page={page}&size={size}",
            headers=self.authorized_chat_headers,
        )

        return resp.status_code, resp.json()

    def get_default_rules(self) -> tuple[int, list[RuleResponse]]:
        uri = "/api/v2/default_rules"
        resp = self.base_client.get(
            url=uri,
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)
        data = resp.json()
        if isinstance(data, list):
            loaded_data = [RuleResponse(**x) for x in data]
        else:
            loaded_data = []

        return (resp.status_code, loaded_data)

    def get_chat_default_task(
        self,
        headers: dict | None = None,
    ) -> tuple[int, ChatDefaultTaskResponse]:
        if headers is None:
            headers = self.authorized_chat_headers
        resp = self.base_client.get(
            "/api/chat/default_task",
            headers=headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                ChatDefaultTaskResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def update_chat_default_task(
        self,
        task_id: str,
        headers: dict | None = None,
    ) -> tuple[int, ChatDefaultTaskResponse]:
        if headers is None:
            headers = self.authorized_chat_headers
        resp = self.base_client.put(
            "/api/chat/default_task",
            json=ChatDefaultTaskRequest(task_id=task_id).model_dump(),
            headers=headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                ChatDefaultTaskResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def receive_traces(self, trace_data: bytes) -> tuple[int, str]:
        """Send OpenInference trace data to the evaluate endpoint.

        Args:
            trace_data: Raw protobuf trace data in bytes

        Returns:
            tuple[int, str]: Status code and response message
        """
        headers = self.authorized_user_api_key_headers.copy()
        headers["Content-Type"] = "application/x-protobuf"

        resp = self.base_client.post(
            "/v1/traces",
            content=trace_data,
            headers=headers,
        )
        log_response(resp)
        return resp.status_code, resp.text

    def query_traces_with_metrics(
        self,
        task_ids: list[str],
        trace_ids: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort: str | None = None,
        tool_name: str | None = None,
        span_types: list | None = None,
        # Query relevance filters
        query_relevance_eq: float | None = None,
        query_relevance_gt: float | None = None,
        query_relevance_gte: float | None = None,
        query_relevance_lt: float | None = None,
        query_relevance_lte: float | None = None,
        # Response relevance filters
        response_relevance_eq: float | None = None,
        response_relevance_gt: float | None = None,
        response_relevance_gte: float | None = None,
        response_relevance_lt: float | None = None,
        response_relevance_lte: float | None = None,
        # Tool classification filters
        tool_selection: int | None = None,
        tool_usage: int | None = None,
        # Trace duration filters
        trace_duration_eq: float | None = None,
        trace_duration_gt: float | None = None,
        trace_duration_gte: float | None = None,
        trace_duration_lt: float | None = None,
        trace_duration_lte: float | None = None,
    ) -> tuple[int, QueryTracesWithMetricsResponse | str]:
        """Query traces with metrics for specified task IDs. Computes metrics for all LLM spans in the traces.

        Args:
            task_ids: Task IDs to filter on (required)
            trace_ids: Trace IDs to filter on (optional)
            start_time: Filter by start time
            end_time: Filter by end time
            page: Page number for pagination
            page_size: Number of items per page
            sort: Sort order ("asc" or "desc")
            tool_name: Return only results with this tool name
            span_types: Span types to filter on (optional)
            query_relevance_eq: Query relevance equal to this value
            query_relevance_gt: Query relevance greater than this value
            query_relevance_gte: Query relevance greater than or equal to this value
            query_relevance_lt: Query relevance less than this value
            query_relevance_lte: Query relevance less than or equal to this value
            response_relevance_eq: Response relevance equal to this value
            response_relevance_gt: Response relevance greater than this value
            response_relevance_gte: Response relevance greater than or equal to this value
            response_relevance_lt: Response relevance less than this value
            response_relevance_lte: Response relevance less than or equal to this value
            tool_selection: Tool selection evaluation result (0=INCORRECT, 1=CORRECT, 2=NA)
            tool_usage: Tool usage evaluation result (0=INCORRECT, 1=CORRECT, 2=NA)
            trace_duration_eq: Duration exactly equal to this value (seconds)
            trace_duration_gt: Duration greater than this value (seconds)
            trace_duration_gte: Duration greater than or equal to this value (seconds)
            trace_duration_lt: Duration less than this value (seconds)
            trace_duration_lte: Duration less than or equal to this value (seconds)

        Returns:
            tuple[int, QueryTracesWithMetricsResponse | str]: Status code and response
        """
        params = {"task_ids": task_ids}
        if trace_ids is not None:
            params["trace_ids"] = trace_ids
        if start_time is not None:
            params["start_time"] = str(start_time)
        if end_time is not None:
            params["end_time"] = str(end_time)
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if sort is not None:
            params["sort"] = sort
        if tool_name is not None:
            params["tool_name"] = tool_name
        if span_types is not None:
            params["span_types"] = span_types
        # Query relevance filters
        if query_relevance_eq is not None:
            params["query_relevance_eq"] = query_relevance_eq
        if query_relevance_gt is not None:
            params["query_relevance_gt"] = query_relevance_gt
        if query_relevance_gte is not None:
            params["query_relevance_gte"] = query_relevance_gte
        if query_relevance_lt is not None:
            params["query_relevance_lt"] = query_relevance_lt
        if query_relevance_lte is not None:
            params["query_relevance_lte"] = query_relevance_lte
        # Response relevance filters
        if response_relevance_eq is not None:
            params["response_relevance_eq"] = response_relevance_eq
        if response_relevance_gt is not None:
            params["response_relevance_gt"] = response_relevance_gt
        if response_relevance_gte is not None:
            params["response_relevance_gte"] = response_relevance_gte
        if response_relevance_lt is not None:
            params["response_relevance_lt"] = response_relevance_lt
        if response_relevance_lte is not None:
            params["response_relevance_lte"] = response_relevance_lte
        # Tool classification filters
        if tool_selection is not None:
            params["tool_selection"] = tool_selection
        if tool_usage is not None:
            params["tool_usage"] = tool_usage
        # Trace duration filters
        if trace_duration_eq is not None:
            params["trace_duration_eq"] = trace_duration_eq
        if trace_duration_gt is not None:
            params["trace_duration_gt"] = trace_duration_gt
        if trace_duration_gte is not None:
            params["trace_duration_gte"] = trace_duration_gte
        if trace_duration_lt is not None:
            params["trace_duration_lt"] = trace_duration_lt
        if trace_duration_lte is not None:
            params["trace_duration_lte"] = trace_duration_lte

        resp = self.base_client.get(
            f"/v1/traces/metrics/?{urllib.parse.urlencode(params, doseq=True)}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                QueryTracesWithMetricsResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def query_traces(
        self,
        task_ids: list[str],
        trace_ids: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort: str | None = None,
        tool_name: str | None = None,
        span_types: list | None = None,
        # Query relevance filters
        query_relevance_eq: float | None = None,
        query_relevance_gt: float | None = None,
        query_relevance_gte: float | None = None,
        query_relevance_lt: float | None = None,
        query_relevance_lte: float | None = None,
        # Response relevance filters
        response_relevance_eq: float | None = None,
        response_relevance_gt: float | None = None,
        response_relevance_gte: float | None = None,
        response_relevance_lt: float | None = None,
        response_relevance_lte: float | None = None,
        # Tool classification filters
        tool_selection: int | None = None,
        tool_usage: int | None = None,
        # Trace duration filters
        trace_duration_eq: float | None = None,
        trace_duration_gt: float | None = None,
        trace_duration_gte: float | None = None,
        trace_duration_lt: float | None = None,
        trace_duration_lte: float | None = None,
    ) -> tuple[int, QueryTracesWithMetricsResponse | str]:
        """Query traces with filters. Task IDs are required. Returns traces with any existing metrics but does not compute new ones.

        Args:
            task_ids: Task IDs to filter on (required)
            trace_ids: Trace IDs to filter on (optional)
            start_time: Filter by start time
            end_time: Filter by end time
            page: Page number for pagination
            page_size: Number of items per page
            sort: Sort order ("asc" or "desc")
            tool_name: Return only results with this tool name
            span_types: Span types to filter on (optional)
            query_relevance_eq: Query relevance equal to this value
            query_relevance_gt: Query relevance greater than this value
            query_relevance_gte: Query relevance greater than or equal to this value
            query_relevance_lt: Query relevance less than this value
            query_relevance_lte: Query relevance less than or equal to this value
            response_relevance_eq: Response relevance equal to this value
            response_relevance_gt: Response relevance greater than this value
            response_relevance_gte: Response relevance greater than or equal to this value
            response_relevance_lt: Response relevance less than this value
            response_relevance_lte: Response relevance less than or equal to this value
            tool_selection: Tool selection evaluation result (0=INCORRECT, 1=CORRECT, 2=NA)
            tool_usage: Tool usage evaluation result (0=INCORRECT, 1=CORRECT, 2=NA)
            trace_duration_eq: Duration exactly equal to this value (seconds)
            trace_duration_gt: Duration greater than this value (seconds)
            trace_duration_gte: Duration greater than or equal to this value (seconds)
            trace_duration_lt: Duration less than this value (seconds)
            trace_duration_lte: Duration less than or equal to this value (seconds)

        Returns:
            tuple[int, QueryTracesWithMetricsResponse | str]: Status code and response
        """
        params = {"task_ids": task_ids}
        if trace_ids is not None:
            params["trace_ids"] = trace_ids
        if start_time is not None:
            params["start_time"] = str(start_time)
        if end_time is not None:
            params["end_time"] = str(end_time)
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if sort is not None:
            params["sort"] = sort
        if tool_name is not None:
            params["tool_name"] = tool_name
        if span_types is not None:
            params["span_types"] = span_types
        # Query relevance filters
        if query_relevance_eq is not None:
            params["query_relevance_eq"] = query_relevance_eq
        if query_relevance_gt is not None:
            params["query_relevance_gt"] = query_relevance_gt
        if query_relevance_gte is not None:
            params["query_relevance_gte"] = query_relevance_gte
        if query_relevance_lt is not None:
            params["query_relevance_lt"] = query_relevance_lt
        if query_relevance_lte is not None:
            params["query_relevance_lte"] = query_relevance_lte
        # Response relevance filters
        if response_relevance_eq is not None:
            params["response_relevance_eq"] = response_relevance_eq
        if response_relevance_gt is not None:
            params["response_relevance_gt"] = response_relevance_gt
        if response_relevance_gte is not None:
            params["response_relevance_gte"] = response_relevance_gte
        if response_relevance_lt is not None:
            params["response_relevance_lt"] = response_relevance_lt
        if response_relevance_lte is not None:
            params["response_relevance_lte"] = response_relevance_lte
        # Tool classification filters
        if tool_selection is not None:
            params["tool_selection"] = tool_selection
        if tool_usage is not None:
            params["tool_usage"] = tool_usage
        # Trace duration filters
        if trace_duration_eq is not None:
            params["trace_duration_eq"] = trace_duration_eq
        if trace_duration_gt is not None:
            params["trace_duration_gt"] = trace_duration_gt
        if trace_duration_gte is not None:
            params["trace_duration_gte"] = trace_duration_gte
        if trace_duration_lt is not None:
            params["trace_duration_lt"] = trace_duration_lt
        if trace_duration_lte is not None:
            params["trace_duration_lte"] = trace_duration_lte

        resp = self.base_client.get(
            f"/v1/traces/query?{urllib.parse.urlencode(params, doseq=True)}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                QueryTracesWithMetricsResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def query_span_metrics(
        self,
        span_id: str,
    ) -> tuple[int, SpanWithMetricsResponse | str]:
        """Compute metrics for a single span. Validates that the span is an LLM span.

        Args:
            span_id: The span ID to compute metrics for

        Returns:
            tuple[int, SpanWithMetricsResponse | str]: Status code and response
        """
        resp = self.base_client.get(
            f"/v1/span/{span_id}/metrics",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                SpanWithMetricsResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def query_spans(
        self,
        task_ids: list[str],
        span_types: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort: str | None = None,
    ) -> tuple[int, QuerySpansResponse | str]:
        """Query spans filtered by span type. Task IDs are required. Returns spans with any existing metrics but does not compute new ones.

        Args:
            task_ids: Task IDs to filter on (required)
            span_types: Span types to filter on (optional)
            start_time: Filter by start time
            end_time: Filter by end time
            page: Page number for pagination
            page_size: Number of items per page
            sort: Sort order ("asc" or "desc")

        Returns:
            tuple[int, QuerySpansResponse | str]: Status code and response
        """
        params = {"task_ids": task_ids}
        if span_types is not None:
            params["span_types"] = span_types
        if start_time is not None:
            params["start_time"] = str(start_time)
        if end_time is not None:
            params["end_time"] = str(end_time)
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if sort is not None:
            params["sort"] = sort

        resp = self.base_client.get(
            f"/v1/spans/query?{urllib.parse.urlencode(params, doseq=True)}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                QuerySpansResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    # ============================================================================
    # NEW TRACE API METHODS (/api/v1/ endpoints)
    # ============================================================================

    def trace_api_receive_traces(self, trace_data: bytes) -> tuple[int, str]:
        """Send OpenInference trace data to the new trace API endpoint.

        Args:
            trace_data: Raw protobuf trace data in bytes

        Returns:
            tuple[int, str]: Status code and response message
        """
        headers = self.authorized_user_api_key_headers.copy()
        headers["Content-Type"] = "application/x-protobuf"

        resp = self.base_client.post(
            "/api/v1/traces",
            content=trace_data,
            headers=headers,
        )
        log_response(resp)
        return resp.status_code, resp.text

    def trace_api_list_traces_metadata(
        self,
        task_ids: list[str],
        trace_ids: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort: str | None = None,
        tool_name: str | None = None,
        span_types: list | None = None,
        user_ids: list[str] | None = None,
        # Query relevance filters
        query_relevance_eq: float | None = None,
        query_relevance_gt: float | None = None,
        query_relevance_gte: float | None = None,
        query_relevance_lt: float | None = None,
        query_relevance_lte: float | None = None,
        # Response relevance filters
        response_relevance_eq: float | None = None,
        response_relevance_gt: float | None = None,
        response_relevance_gte: float | None = None,
        response_relevance_lt: float | None = None,
        response_relevance_lte: float | None = None,
        # Tool classification filters
        tool_selection: int | None = None,
        tool_usage: int | None = None,
        # Trace duration filters
        trace_duration_eq: float | None = None,
        trace_duration_gt: float | None = None,
        trace_duration_gte: float | None = None,
        trace_duration_lt: float | None = None,
        trace_duration_lte: float | None = None,
    ) -> tuple[int, TraceListResponse | str]:
        """Get lightweight trace metadata for browsing/filtering operations.

        Returns:
            tuple[int, TraceListResponse | str]: Status code and response
        """
        params = {"task_ids": task_ids}
        if trace_ids is not None:
            params["trace_ids"] = trace_ids
        if start_time is not None:
            params["start_time"] = str(start_time)
        if end_time is not None:
            params["end_time"] = str(end_time)
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if sort is not None:
            params["sort"] = sort
        if tool_name is not None:
            params["tool_name"] = tool_name
        if span_types is not None:
            params["span_types"] = span_types
        if user_ids is not None:
            params["user_ids"] = user_ids
        # Query relevance filters
        if query_relevance_eq is not None:
            params["query_relevance_eq"] = query_relevance_eq
        if query_relevance_gt is not None:
            params["query_relevance_gt"] = query_relevance_gt
        if query_relevance_gte is not None:
            params["query_relevance_gte"] = query_relevance_gte
        if query_relevance_lt is not None:
            params["query_relevance_lt"] = query_relevance_lt
        if query_relevance_lte is not None:
            params["query_relevance_lte"] = query_relevance_lte
        # Response relevance filters
        if response_relevance_eq is not None:
            params["response_relevance_eq"] = response_relevance_eq
        if response_relevance_gt is not None:
            params["response_relevance_gt"] = response_relevance_gt
        if response_relevance_gte is not None:
            params["response_relevance_gte"] = response_relevance_gte
        if response_relevance_lt is not None:
            params["response_relevance_lt"] = response_relevance_lt
        if response_relevance_lte is not None:
            params["response_relevance_lte"] = response_relevance_lte
        # Tool classification filters
        if tool_selection is not None:
            params["tool_selection"] = tool_selection
        if tool_usage is not None:
            params["tool_usage"] = tool_usage
        # Trace duration filters
        if trace_duration_eq is not None:
            params["trace_duration_eq"] = trace_duration_eq
        if trace_duration_gt is not None:
            params["trace_duration_gt"] = trace_duration_gt
        if trace_duration_gte is not None:
            params["trace_duration_gte"] = trace_duration_gte
        if trace_duration_lt is not None:
            params["trace_duration_lt"] = trace_duration_lt
        if trace_duration_lte is not None:
            params["trace_duration_lte"] = trace_duration_lte

        resp = self.base_client.get(
            f"/api/v1/traces?{urllib.parse.urlencode(params, doseq=True)}",
            headers=self.authorized_user_api_key_headers,
        )

        # below filled in
        log_response(resp)

        return (
            resp.status_code,
            (
                TraceListResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def trace_api_get_trace_by_id(
        self,
        trace_id: str,
    ) -> tuple[int, TraceResponse | str]:
        """Get complete trace tree with existing metrics (no computation).

        Args:
            trace_id: The trace ID to retrieve

        Returns:
            tuple[int, TraceResponse | str]: Status code and response
        """
        resp = self.base_client.get(
            f"/api/v1/traces/{trace_id}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                TraceResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def trace_api_compute_trace_metrics(
        self,
        trace_id: str,
    ) -> tuple[int, TraceResponse | str]:
        """Compute all missing metrics for trace spans on-demand.

        Args:
            trace_id: The trace ID to compute metrics for

        Returns:
            tuple[int, TraceResponse | str]: Status code and response
        """
        resp = self.base_client.get(
            f"/api/v1/traces/{trace_id}/metrics",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                TraceResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def trace_api_list_spans_metadata(
        self,
        task_ids: list[str],
        trace_ids: list[str] | None = None,
        span_types: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort: str | None = None,
        tool_name: str | None = None,
        # Query relevance filters
        query_relevance_eq: float | None = None,
        query_relevance_gt: float | None = None,
        query_relevance_gte: float | None = None,
        query_relevance_lt: float | None = None,
        query_relevance_lte: float | None = None,
        # Response relevance filters
        response_relevance_eq: float | None = None,
        response_relevance_gt: float | None = None,
        response_relevance_gte: float | None = None,
        response_relevance_lt: float | None = None,
        response_relevance_lte: float | None = None,
        # Tool classification filters
        tool_selection: int | None = None,
        tool_usage: int | None = None,
        # Trace duration filters
        trace_duration_eq: float | None = None,
        trace_duration_gt: float | None = None,
        trace_duration_gte: float | None = None,
        trace_duration_lt: float | None = None,
        trace_duration_lte: float | None = None,
    ) -> tuple[int, SpanListResponse | str]:
        """Get lightweight span metadata with comprehensive filtering support.

        Args:
            task_ids: Task IDs to filter on (required)
            trace_ids: Trace IDs to filter on (optional)
            span_types: Span types to filter on (optional)
            start_time: Filter by start time
            end_time: Filter by end time
            page: Page number for pagination
            page_size: Number of items per page
            sort: Sort order ("asc" or "desc")
            tool_name: Return only results with this tool name
            query_relevance_eq: Query relevance equal to this value
            query_relevance_gt: Query relevance greater than this value
            query_relevance_gte: Query relevance greater than or equal to this value
            query_relevance_lt: Query relevance less than this value
            query_relevance_lte: Query relevance less than or equal to this value
            response_relevance_eq: Response relevance equal to this value
            response_relevance_gt: Response relevance greater than this value
            response_relevance_gte: Response relevance greater than or equal to this value
            response_relevance_lt: Response relevance less than this value
            response_relevance_lte: Response relevance less than or equal to this value
            tool_selection: Tool selection evaluation result (0=INCORRECT, 1=CORRECT, 2=NA)
            tool_usage: Tool usage evaluation result (0=INCORRECT, 1=CORRECT, 2=NA)
            trace_duration_eq: Duration exactly equal to this value (seconds)
            trace_duration_gt: Duration greater than this value (seconds)
            trace_duration_gte: Duration greater than or equal to this value (seconds)
            trace_duration_lt: Duration less than this value (seconds)
            trace_duration_lte: Duration less than or equal to this value (seconds)

        Returns:
            tuple[int, SpanListResponse | str]: Status code and response
        """
        params = {"task_ids": task_ids}
        if trace_ids is not None:
            params["trace_ids"] = trace_ids
        if span_types is not None:
            params["span_types"] = span_types
        if start_time is not None:
            params["start_time"] = str(start_time)
        if end_time is not None:
            params["end_time"] = str(end_time)
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if sort is not None:
            params["sort"] = sort
        if tool_name is not None:
            params["tool_name"] = tool_name
        # Query relevance filters
        if query_relevance_eq is not None:
            params["query_relevance_eq"] = query_relevance_eq
        if query_relevance_gt is not None:
            params["query_relevance_gt"] = query_relevance_gt
        if query_relevance_gte is not None:
            params["query_relevance_gte"] = query_relevance_gte
        if query_relevance_lt is not None:
            params["query_relevance_lt"] = query_relevance_lt
        if query_relevance_lte is not None:
            params["query_relevance_lte"] = query_relevance_lte
        # Response relevance filters
        if response_relevance_eq is not None:
            params["response_relevance_eq"] = response_relevance_eq
        if response_relevance_gt is not None:
            params["response_relevance_gt"] = response_relevance_gt
        if response_relevance_gte is not None:
            params["response_relevance_gte"] = response_relevance_gte
        if response_relevance_lt is not None:
            params["response_relevance_lt"] = response_relevance_lt
        if response_relevance_lte is not None:
            params["response_relevance_lte"] = response_relevance_lte
        # Tool classification filters
        if tool_selection is not None:
            params["tool_selection"] = tool_selection
        if tool_usage is not None:
            params["tool_usage"] = tool_usage
        # Trace duration filters
        if trace_duration_eq is not None:
            params["trace_duration_eq"] = trace_duration_eq
        if trace_duration_gt is not None:
            params["trace_duration_gt"] = trace_duration_gt
        if trace_duration_gte is not None:
            params["trace_duration_gte"] = trace_duration_gte
        if trace_duration_lt is not None:
            params["trace_duration_lt"] = trace_duration_lt
        if trace_duration_lte is not None:
            params["trace_duration_lte"] = trace_duration_lte

        resp = self.base_client.get(
            f"/api/v1/traces/spans?{urllib.parse.urlencode(params, doseq=True)}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                SpanListResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def trace_api_get_span_by_id(
        self,
        span_id: str,
    ) -> tuple[int, SpanWithMetricsResponse | str]:
        """Get single span with existing metrics (no computation).

        Args:
            span_id: The span ID to retrieve

        Returns:
            tuple[int, SpanWithMetricsResponse | str]: Status code and response
        """
        resp = self.base_client.get(
            f"/api/v1/traces/spans/{span_id}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                SpanWithMetricsResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def trace_api_compute_span_metrics(
        self,
        span_id: str,
    ) -> tuple[int, SpanWithMetricsResponse | str]:
        """Compute all missing metrics for a single span on-demand.

        Args:
            span_id: The span ID to compute metrics for

        Returns:
            tuple[int, SpanWithMetricsResponse | str]: Status code and response
        """
        resp = self.base_client.get(
            f"/api/v1/traces/spans/{span_id}/metrics",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                SpanWithMetricsResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def trace_api_list_sessions_metadata(
        self,
        task_ids: list[str],
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort: str | None = None,
        user_ids: list[str] | None = None,
    ) -> tuple[int, SessionListResponse | str]:
        """Get session metadata with pagination and filtering.

        Args:
            task_ids: Task IDs to filter on (required)
            start_time: Filter by start time
            end_time: Filter by end time
            page: Page number for pagination
            page_size: Number of items per page
            sort: Sort order ("asc" or "desc")

        Returns:
            tuple[int, SessionListResponse | str]: Status code and response
        """
        params = {"task_ids": task_ids}
        if start_time is not None:
            params["start_time"] = str(start_time)
        if end_time is not None:
            params["end_time"] = str(end_time)
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if sort is not None:
            params["sort"] = sort
        if user_ids is not None:
            params["user_ids"] = user_ids

        resp = self.base_client.get(
            f"/api/v1/traces/sessions?{urllib.parse.urlencode(params, doseq=True)}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                SessionListResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def trace_api_get_user_details(
        self,
        user_id: str,
        task_ids: list[str],
    ) -> tuple[int, TraceUserMetadataResponse | str]:
        """Get detailed information for a single user.

        Args:
            user_id: User ID to get details for
            task_ids: Task IDs to filter on (required)

        Returns:
            tuple[int, TraceUserMetadataResponse | str]: Status code and response
        """
        params = {"task_ids": task_ids}

        resp = self.base_client.get(
            f"/api/v1/traces/users/{user_id}?{urllib.parse.urlencode(params, doseq=True)}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                TraceUserMetadataResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def trace_api_get_session_traces(
        self,
        session_id: str,
        page: int | None = None,
        page_size: int | None = None,
        sort: str | None = None,
    ) -> tuple[int, SessionTracesResponse | str]:
        """Get all traces in a session with existing metrics (no computation).

        Args:
            session_id: The session ID to retrieve traces for
            page: Page number for pagination
            page_size: Number of items per page
            sort: Sort order ("asc" or "desc")

        Returns:
            tuple[int, SessionTracesResponse | str]: Status code and response
        """
        params = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if sort is not None:
            params["sort"] = sort

        query_string = (
            f"?{urllib.parse.urlencode(params, doseq=True)}" if params else ""
        )
        resp = self.base_client.get(
            f"/api/v1/traces/sessions/{session_id}{query_string}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                SessionTracesResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def trace_api_compute_session_metrics(
        self,
        session_id: str,
        page: int | None = None,
        page_size: int | None = None,
        sort: str | None = None,
    ) -> tuple[int, SessionTracesResponse | str]:
        """Get all traces in a session and compute missing metrics.

        Args:
            session_id: The session ID to compute metrics for
            page: Page number for pagination
            page_size: Number of items per page
            sort: Sort order ("asc" or "desc")

        Returns:
            tuple[int, SessionTracesResponse | str]: Status code and response
        """
        params = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if sort is not None:
            params["sort"] = sort

        query_string = (
            f"?{urllib.parse.urlencode(params, doseq=True)}" if params else ""
        )
        resp = self.base_client.get(
            f"/api/v1/traces/sessions/{session_id}/metrics{query_string}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                SessionTracesResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def trace_api_list_users_metadata(
        self,
        task_ids: list[str],
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort: str | None = None,
    ):
        """List user metadata via Trace API.

        Args:
            task_ids: List of task IDs to filter on
            start_time: Optional start time filter
            end_time: Optional end time filter
            page: Page number for pagination
            page_size: Number of items per page
            sort: Sort order ("asc" or "desc")

        Returns:
            tuple[int, TraceUserListResponse | str]: Status code and response
        """

        params = {"task_ids": task_ids}
        if start_time is not None:
            params["start_time"] = start_time.isoformat()
        if end_time is not None:
            params["end_time"] = end_time.isoformat()
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if sort is not None:
            params["sort"] = sort

        query_string = (
            f"?{urllib.parse.urlencode(params, doseq=True)}" if params else ""
        )
        resp = self.base_client.get(
            f"/api/v1/traces/users{query_string}",
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                TraceUserListResponse.model_validate(resp.json())
                if resp.status_code == 200
                else resp.text
            ),
        )

    def create_dataset_version(
        self,
        dataset_id: str,
        rows_to_add: list[NewDatasetVersionRowRequest] = None,
        rows_to_delete: list[str] = None,
        rows_to_update: list[NewDatasetVersionUpdateRowRequest] = None,
    ) -> tuple[int, DatasetVersionResponse]:
        """Create a new dataset version."""
        if rows_to_add is None:
            rows_to_add = []
        if rows_to_delete is None:
            rows_to_delete = []
        if rows_to_update is None:
            rows_to_update = []

        request = NewDatasetVersionRequest(
            rows_to_add=rows_to_add,
            rows_to_delete=rows_to_delete,
            rows_to_update=rows_to_update,
        )

        resp = self.base_client.post(
            f"/api/v2/datasets/{dataset_id}/versions",
            data=request.model_dump_json(),
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                DatasetVersionResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def get_dataset_version(
        self,
        dataset_id: str,
        version_number: int,
        page: int = None,
        page_size: int = None,
    ) -> tuple[int, DatasetVersionResponse]:
        """Get a dataset version."""
        path = f"/api/v2/datasets/{dataset_id}/versions/{version_number}"
        params = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size

        url = path
        if params:
            url = f"{path}?{urllib.parse.urlencode(params)}"

        resp = self.base_client.get(
            url,
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                DatasetVersionResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def get_dataset_versions(
        self,
        dataset_id: str,
        page: int = None,
        page_size: int = None,
        latest_version_only: bool = False,
    ) -> tuple[int, ListDatasetVersionsResponse]:
        """Get dataset versions for a dataset."""
        path = f"/api/v2/datasets/{dataset_id}/versions"
        params = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if latest_version_only:
            params["latest_version_only"] = latest_version_only

        url = path
        if params:
            url = f"{path}?{urllib.parse.urlencode(params)}"

        resp = self.base_client.get(
            url,
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                ListDatasetVersionsResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def create_rag_provider(
        self,
        task_id: str,
        name: str,
        description: str = None,
        authentication_method: RagProviderAuthenticationMethodEnum = RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION,
        api_key: str = "test-api-key",
        host_url: str = "https://test-weaviate.example.com",
        rag_provider: RagAPIKeyAuthenticationProviderEnum = RagAPIKeyAuthenticationProviderEnum.WEAVIATE,
    ) -> tuple[int, RagProviderConfigurationResponse]:
        """Create a new RAG provider configuration."""
        auth_config = ApiKeyRagAuthenticationConfigRequest(
            api_key=api_key,
            host_url=host_url,
            rag_provider=rag_provider,
        )

        request = RagProviderConfigurationRequest(
            name=name,
            description=description,
            authentication_method=authentication_method,
            authentication_config=auth_config,
        )

        resp = self.base_client.post(
            f"/api/v1/tasks/{task_id}/rag_providers",
            data=request.model_dump_json(),
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                RagProviderConfigurationResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def get_rag_provider(
        self,
        provider_id: str,
    ) -> tuple[int, RagProviderConfigurationResponse]:
        """Get a RAG provider configuration by ID."""
        resp = self.base_client.get(
            f"/api/v1/rag_providers/{provider_id}",
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                RagProviderConfigurationResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def update_rag_provider(
        self,
        provider_id: str,
        name: str = None,
        description: str = None,
        authentication_method: RagProviderAuthenticationMethodEnum = None,
        api_key: str = None,
        host_url: str = None,
        rag_provider: RagAPIKeyAuthenticationProviderEnum = None,
    ) -> tuple[int, RagProviderConfigurationResponse]:
        """Update a RAG provider configuration."""
        auth_config = None
        if any([api_key, host_url, rag_provider]):
            auth_config = ApiKeyRagAuthenticationConfigUpdateRequest(
                api_key=api_key,
                host_url=host_url,
                rag_provider=rag_provider,
            )

        request = RagProviderConfigurationUpdateRequest(
            name=name,
            description=description,
            authentication_method=authentication_method,
            authentication_config=auth_config,
        )

        resp = self.base_client.patch(
            f"/api/v1/rag_providers/{provider_id}",
            data=request.model_dump_json(),
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                RagProviderConfigurationResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def delete_rag_provider(self, provider_id: str) -> int:
        """Delete a RAG provider configuration."""
        resp = self.base_client.delete(
            f"/api/v1/rag_providers/{provider_id}",
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return resp.status_code

    def search_rag_providers(
        self,
        task_id: str,
        sort: PaginationSortMethod = None,
        page: int = None,
        page_size: int = None,
        config_name: str = None,
        authentication_method: RagProviderAuthenticationMethodEnum = None,
        rag_provider_name: RagAPIKeyAuthenticationProviderEnum = None,
    ) -> tuple[int, SearchRagProviderConfigurationsResponse]:
        """Search RAG provider configurations for a task."""
        path = f"api/v1/tasks/{task_id}/rag_providers"
        params = get_base_pagination_parameters(
            sort=sort,
            page=page,
            page_size=page_size,
        )
        if config_name:
            params["config_name"] = config_name
        if authentication_method:
            params["authentication_method"] = authentication_method
        if rag_provider_name:
            params["rag_provider_name"] = rag_provider_name

        resp = self.base_client.get(
            "{}{}".format(
                path,
                "?" + urllib.parse.urlencode(params, doseq=True) if params else "",
            ),
            headers=self.authorized_user_api_key_headers,
        )
        log_response(resp)

        return (
            resp.status_code,
            (
                SearchRagProviderConfigurationsResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def test_rag_provider_connection(
        self,
        task_id: str,
        name: str,
        description: str = None,
        authentication_method: RagProviderAuthenticationMethodEnum = RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION,
        api_key: str = "test-api-key",
        host_url: str = "https://test-weaviate.example.com",
        rag_provider: RagAPIKeyAuthenticationProviderEnum = RagAPIKeyAuthenticationProviderEnum.WEAVIATE,
    ) -> tuple[int, ConnectionCheckResult]:
        """Test a RAG provider connection configuration."""
        auth_config = ApiKeyRagAuthenticationConfigRequest(
            api_key=api_key,
            host_url=host_url,
            rag_provider=rag_provider,
        )

        request = RagProviderConfigurationRequest(
            name=name,
            description=description,
            authentication_method=authentication_method,
            authentication_config=auth_config,
        )

        resp = self.base_client.post(
            f"/api/v1/tasks/{task_id}/rag_providers/test_connection",
            data=request.model_dump_json(),
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                ConnectionCheckResult.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def execute_similarity_text_search(
        self,
        provider_id: str,
        query: str,
        collection_name: str,
        certainty: float = None,
        limit: int = None,
        include_vector: bool = False,
        offset: int = None,
        distance: float = None,
        auto_limit: int = None,
        move_to: dict = None,
        move_away: dict = None,
    ) -> tuple[int, RagProviderQueryResponse]:
        """Execute a similarity text search on a RAG provider."""
        weaviate_settings = WeaviateVectorSimilarityTextSearchSettingsRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name=collection_name,
            query=query,
            certainty=certainty,
            limit=limit,
            include_vector=include_vector,
            offset=offset,
            distance=distance,
            auto_limit=auto_limit,
            move_to=move_to,
            move_away=move_away,
        )

        request = RagVectorSimilarityTextSearchSettingRequest(
            settings=weaviate_settings,
        )

        resp = self.base_client.post(
            f"/api/v1/rag_providers/{provider_id}/similarity_text_search",
            data=request.model_dump_json(),
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                RagProviderQueryResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )

    def execute_keyword_search(
        self,
        provider_id: str,
        query: str,
        collection_name: str,
        limit: int = None,
        include_vector: bool = False,
        offset: int = None,
        auto_limit: int = None,
        minimum_match_or_operator: int = None,
        and_operator: bool = None,
    ) -> tuple[int, RagProviderQueryResponse]:
        """Execute a keyword search on a RAG provider."""
        weaviate_settings = WeaviateKeywordSearchSettingsRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name=collection_name,
            query=query,
            limit=limit,
            include_vector=include_vector,
            offset=offset,
            auto_limit=auto_limit,
            minimum_match_or_operator=minimum_match_or_operator,
            and_operator=and_operator,
        )

        request = RagKeywordSearchSettingRequest(
            settings=weaviate_settings,
        )

        resp = self.base_client.post(
            f"/api/v1/rag_providers/{provider_id}/keyword_search",
            data=request.model_dump_json(),
            headers=self.authorized_user_api_key_headers,
        )

        log_response(resp)

        return (
            resp.status_code,
            (
                RagProviderQueryResponse.model_validate(resp.json())
                if resp.status_code == 200
                else None
            ),
        )


def get_base_pagination_parameters(
    sort: PaginationSortMethod = None,
    page: int = None,
    page_size: int = None,
) -> dict:
    params = {}
    if sort is not None:
        params["sort"] = sort
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["page_size"] = page_size

    return params


def log_response(response: httpx.Response):
    print("Response:")
    print("\t", response.request.method, response.url, response.status_code)
    if constants.RESPONSE_TRACE_ID_HEADER in response.headers:
        print(
            f"\tResponse trace id: {response.headers[constants.RESPONSE_TRACE_ID_HEADER]}",
        )
