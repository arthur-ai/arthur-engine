import json
from abc import ABC, abstractmethod
from datetime import datetime
from logging import Logger
from typing import Any, Optional
from urllib.parse import urlparse

import genai_client.exceptions
import pandas as pd
from arthur_client.api_bindings import (
    AvailableDataset,
    ConnectorCheckOutcome,
    ConnectorCheckResult,
    ConnectorSpec,
    ContinuousEvalResponse,
    DataResultFilter,
    Dataset,
    DatasetLocator,
    DatasetLocatorField,
    LLMEval,
    PutAvailableDataset,
    PutAvailableDatasets,
    TraceTransformResponse,
)
from arthur_common.models.connectors import (
    SHIELD_CONNECTOR_API_KEY_FIELD,
    SHIELD_CONNECTOR_ENDPOINT_FIELD,
    SHIELD_DATASET_TASK_ID_FIELD,
    ConnectorPaginationOptions,
)
from arthur_common.models.enums import ModelProblemType
from arthur_common.models.request_schemas import (
    AgentMetadata,
)
from arthur_common.models.request_schemas import (
    NewMetricRequest as ArthurCommonNewMetricRequest,
)
from arthur_common.models.request_schemas import (
    NewRuleRequest,
)
from arthur_common.models.response_schemas import (
    MetricResponse as ArthurCommonMetricResponse,
)
from arthur_common.models.response_schemas import (
    RuleResponse,
    TaskResponse,
)
from genai_client import (
    ApiClient,
    APIKeysApi,
    Configuration,
    ContinuousEvalsApi,
    InferencesApi,
    LLMEvalsApi,
    SpansApi,
    TasksApi,
    TracesApi,
    TransformsApi,
)
from genai_client.exceptions import (
    ForbiddenException,
    ServiceException,
    UnauthorizedException,
)
from genai_client.models import (
    ApiKeyResponse,
    APIKeysRolesEnum,
    LLMGetAllMetadataListResponse,
    NewApiKeyRequest,
    NewTaskRequest,
    RuleType,
    SearchTasksRequest,
    UpdateRuleRequest,
)
from pydantic import ValidationError

from config.config import Config
from connectors.connector import Connector
from tools.agentic_filters import (
    SHIELD_SORT_FILTER,
    add_default_sort_filter,
    build_and_validate_agentic_filter_params,
    validate_filters,
)
from tools.api_client_type_converters import ShieldClientTypeConverter

SHIELD_MAX_PAGE_SIZE = 1500


class ShieldBaseConnector(Connector, ABC):
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        connector_config: ConnectorSpec,
        logger: Logger,
    ) -> None:
        self.logger = logger
        self.connector_config = connector_config
        shield_api_config = Configuration(
            host=self._strip_and_validate_endpoint(endpoint),
            access_token=api_key,
        )
        self._genai_client = ApiClient(configuration=shield_api_config)
        self._inferences_client = InferencesApi(api_client=self._genai_client)
        self._tasks_client = TasksApi(api_client=self._genai_client)
        self._api_keys_client = APIKeysApi(api_client=self._genai_client)
        self._spans_client = SpansApi(api_client=self._genai_client)
        self._traces_client = TracesApi(api_client=self._genai_client)
        self._evals_client = LLMEvalsApi(api_client=self._genai_client)
        self._cont_evals_client = ContinuousEvalsApi(api_client=self._genai_client)
        self._transforms_client = TransformsApi(api_client=self._genai_client)

    @staticmethod
    def _strip_and_validate_endpoint(endpoint: str) -> str:
        endpoint_components = urlparse(endpoint)
        missing_components = []
        if not endpoint_components.scheme:
            missing_components.append("scheme")
        if not endpoint_components.hostname:
            missing_components.append("hostname")
        if missing_components:
            raise ValueError(
                f"Invalid endpoint: {endpoint}. Endpoint does not include {', '.join(missing_components)}.",
            )
        if endpoint_components.port:
            return f"{endpoint_components.scheme}://{endpoint_components.hostname}:{endpoint_components.port}"
        return f"{endpoint_components.scheme}://{endpoint_components.hostname}"

    def read(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        filters: list[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        """
        Reads data from the shield /api/v1/inferences/query endpoint. By default, will fetch all data between start/end
        matching the filters. If the pagination is set, it will only fetch that single page. Note that it
        may return less than page_size rows if there is not enough data in the query.
        Starts from end_time and works backward.
        """
        if not dataset.dataset_locator:
            raise ValueError(
                f"Dataset {dataset.id} has no dataset locator, cannot read from Shield.",
            )

        is_agentic = dataset.model_problem_type == ModelProblemType.AGENTIC_TRACE
        key = "traces" if is_agentic else "inferences"
        paginated_data: list[dict[str, Any]] = []

        dataset_locator_fields = {
            f.key: f.value for f in dataset.dataset_locator.fields
        }

        params: dict[str, Any] = {
            "page_size": SHIELD_MAX_PAGE_SIZE,
        }

        filters = add_default_sort_filter(filters)
        filters = validate_filters(filters, is_agentic=is_agentic)
        params.update(**{f.field_name: f.value for f in filters})

        single_page_requested = pagination_options is not None

        if pagination_options:
            page, page_size = pagination_options.page_params
            params["page"] = page - 1
            params["page_size"] = page_size
        else:
            params["page"] = 0
            params["page_size"] = SHIELD_MAX_PAGE_SIZE

        page_size = params["page_size"]

        resp: Any = None

        while True:
            if is_agentic:
                try:
                    # Build and validate filter parameters directly
                    filter_params = build_and_validate_agentic_filter_params(
                        filters=filters or [],
                    )

                    self.logger.info(
                        f"Fetching page {params['page']} of traces with {len(filter_params)} filters",
                    )
                    resp = self._traces_client.list_traces_metadata_api_v1_traces_get_with_http_info(
                        task_ids=[dataset_locator_fields[SHIELD_DATASET_TASK_ID_FIELD]],
                        include_spans=True,
                        start_time=start_time,
                        end_time=end_time,
                        page=params["page"],
                        page_size=params["page_size"],
                        sort=params.get(SHIELD_SORT_FILTER),
                        **filter_params,  # Only the validated filter parameters
                    )

                except ValidationError as e:
                    self.logger.error(f"Trace query validation failed: {e}")
                    raise

            else:
                # use raw http info so we can load JSON directly to avoid API types
                self.logger.info(f"Fetching page {params['page']} of inferences")
                resp = self._inferences_client.query_inferences_api_v2_inferences_query_get_with_http_info(
                    # required params
                    task_ids=[dataset_locator_fields[SHIELD_DATASET_TASK_ID_FIELD]],
                    start_time=start_time,
                    end_time=end_time,
                    include_count=False,
                    page=params["page"],
                    page_size=params["page_size"],
                    # optional filters
                    conversation_id=params.get("conversation_id"),
                    inference_id=params.get("inference_id"),
                    user_id=params.get("user_id"),
                    rule_types=[
                        RuleType(rule_type)
                        for rule_type in params.get("rule_types", [])
                    ],
                    rule_statuses=params.get("rule_statuses"),
                    prompt_statuses=params.get("prompt_statuses"),
                    response_statuses=params.get("response_statuses"),
                    sort=params.get(SHIELD_SORT_FILTER),
                )
            self.logger.info(f"Read response code: {resp.status_code}")
            # load raw JSON response
            paginated_data.extend(json.loads(resp.raw_data)[key])

            if single_page_requested:
                paginated_data = paginated_data[:page_size]
                break

            # if the request returned fewer items than asked for, we've reached the end
            if len(getattr(resp.data, key)) < page_size:
                break

            params["page"] += 1

        return paginated_data

    def test_connection(self) -> ConnectorCheckResult:
        try:
            self._inferences_client.query_inferences_api_v2_inferences_query_get(
                page_size=1,
                _request_timeout=1,
            )
        except (ForbiddenException, UnauthorizedException) as e:
            self.logger.error(
                f"Failed to connect to Shield, received response: {e.body}",
            )
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason="Bad Credentials",
            )
        except ServiceException as e:
            self.logger.error(
                f"Failed to connect to Shield, received 500 response: {e.body}",
            )
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason="Server Error",
            )
        # catch all
        # catch connection exceptions
        except Exception as e:
            self.logger.error(
                f"Failed to connect to {self._genai_client.configuration.host}",
                exc_info=e,
            )
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason=f"Could not connect to endpoint: {self._genai_client.configuration.host}",
            )

        return ConnectorCheckResult(
            connection_check_outcome=ConnectorCheckOutcome.SUCCEEDED,
        )

    def list_datasets(self) -> PutAvailableDatasets:
        page_size, page = 250, 0
        datasets: PutAvailableDatasets = PutAvailableDatasets(available_datasets=[])
        while True:
            resp = self._tasks_client.search_tasks_api_v2_tasks_search_post(
                search_tasks_request=SearchTasksRequest(
                    task_ids=[],
                    task_name="",
                ),
                page_size=page_size,
                page=page,
            )
            for task in resp.tasks:
                model_problem_type = (
                    ModelProblemType.AGENTIC_TRACE
                    if task.is_agentic
                    else ModelProblemType.ARTHUR_SHIELD
                )
                datasets.available_datasets.append(
                    PutAvailableDataset(
                        name=task.name,
                        dataset_locator=DatasetLocator(
                            fields=[
                                DatasetLocatorField(
                                    key=SHIELD_DATASET_TASK_ID_FIELD,
                                    value=task.id,
                                ),
                            ],
                        ),
                        model_problem_type=model_problem_type,
                    ),
                )

            if len(resp.tasks) != page_size:
                break

            page += 1
        return datasets

    def create_task(
        self,
        name: str,
        is_agentic: bool = False,
        agent_metadata: Optional[AgentMetadata] = None,
    ) -> TaskResponse:
        # Serialize to dict to bridge the gap between arthur_common and generated client types
        agent_metadata_dict = agent_metadata.model_dump() if agent_metadata else None
        new_task_req = NewTaskRequest(
            name=name,
            is_agentic=is_agentic,
            agent_metadata=agent_metadata_dict,  # type: ignore[arg-type]
        )
        resp = self._tasks_client.create_task_api_v2_tasks_post_with_http_info(
            new_task_request=new_task_req,
        )
        task_response = TaskResponse.model_validate_json(resp.raw_data)
        return task_response

    def read_task(self, task_id: str) -> TaskResponse:
        resp = self._tasks_client.get_task_api_v2_tasks_task_id_get_with_http_info(
            task_id=task_id,
        )
        return TaskResponse.model_validate_json(resp.raw_data)

    def delete_task(self, task_id: str) -> None:
        self._tasks_client.archive_task_api_v2_tasks_task_id_delete(task_id=task_id)

    def add_rule_to_task(self, task_id: str, new_rule: NewRuleRequest) -> RuleResponse:
        resp = self._tasks_client.create_task_rule_api_v2_tasks_task_id_rules_post_with_http_info(
            task_id=task_id,
            new_rule_request=ShieldClientTypeConverter.new_rule_request_api_to_shield_client(
                new_rule,
            ),
        )
        return RuleResponse.model_validate_json(resp.raw_data)

    def update_task_rule(
        self,
        task_id: str,
        rule_id: str,
        enabled: bool,
    ) -> TaskResponse:
        resp = self._tasks_client.update_task_rules_api_v2_tasks_task_id_rules_rule_id_patch_with_http_info(
            task_id=task_id,
            rule_id=rule_id,
            update_rule_request=UpdateRuleRequest(enabled=enabled),
        )
        return TaskResponse.model_validate_json(resp.raw_data)

    def enable_task_rule(self, task_id: str, rule_id: str) -> TaskResponse:
        return self.update_task_rule(task_id, rule_id, True)

    def disable_task_rule(self, task_id: str, rule_id: str) -> TaskResponse:
        return self.update_task_rule(task_id, rule_id, False)

    def delete_task_rule(self, task_id: str, rule_id: str) -> None:
        self._tasks_client.archive_task_rule_api_v2_tasks_task_id_rules_rule_id_delete(
            task_id=task_id,
            rule_id=rule_id,
        )

    def add_metric_to_task(
        self,
        task_id: str,
        new_metric: ArthurCommonNewMetricRequest,
    ) -> ArthurCommonMetricResponse:
        try:
            response = self._tasks_client.create_task_metric_api_v2_tasks_task_id_metrics_post_with_http_info(
                task_id=task_id,
                new_metric_request=ShieldClientTypeConverter.new_metric_request_api_to_shield_client(
                    new_metric,
                ),
            )
            return ArthurCommonMetricResponse.model_validate_json(response.raw_data)
        except Exception as e:
            self.logger.error(f"Failed to add metric to task {task_id}: {e}")
            raise

    def delete_task_metric(self, task_id: str, metric_id: str) -> None:
        try:
            self._tasks_client.archive_task_metric_api_v2_tasks_task_id_metrics_metric_id_delete(
                task_id=task_id,
                metric_id=metric_id,
            )
        except Exception as e:
            self.logger.error(
                f"Failed to delete metric {metric_id} from task {task_id}: {e}",
            )
            raise

    def create_task_validation_key(self, task_id: str) -> ApiKeyResponse:
        api_key_resp = self._api_keys_client.create_api_key_auth_api_keys_post(
            new_api_key_request=NewApiKeyRequest(
                description=f"Task Validation Key - {task_id}",
                roles=[APIKeysRolesEnum.VALIDATION_MINUS_USER],
            ),
        )
        return api_key_resp

    def delete_task_validation_key(self, api_key_id: str) -> None:
        try:
            self._api_keys_client.deactivate_api_key_auth_api_keys_deactivate_api_key_id_delete(
                api_key_id=api_key_id,
            )
        except (
            genai_client.exceptions.NotFoundException,
            genai_client.exceptions.BadRequestException,
        ):
            # delete is idempotent
            pass

    def read_llm_evals(
        self,
        task_id: str,
        page: int | None = None,
        page_size: int | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
    ) -> LLMGetAllMetadataListResponse:
        """
        Reads LLM evaluation definitions from the Shield API.

        Args:
            task_id: Task ID to query
            page: Page number for pagination (optional)
            page_size: Number of items per page (optional)
            created_after: Inclusive start date in ISO8601 format (optional)
            created_before: Exclusive end date in ISO8601 format (optional)

        Returns:
            LLMGetAllMetadataListResponse containing LLM eval metadata
        """
        return self._evals_client.get_all_llm_evals_api_v1_tasks_task_id_llm_evals_get(
            task_id=task_id,
            page=page,
            page_size=page_size,
            created_after=created_after,
            created_before=created_before,
        )

    def read_llm_eval_latest_version(
        self,
        task_id: str,
        eval_name: str,
    ) -> LLMEval:
        """
        Reads the latest version of a specific LLM evaluation from the Shield API.

        Args:
            task_id: Task ID to query
            eval_name: Name of the eval to retrieve

        Returns:
            LLMEval object for the latest version
        """
        resp = self._evals_client.get_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_get_with_http_info(
            task_id=task_id,
            eval_name=eval_name,
            eval_version="latest",
        )
        data = json.loads(resp.raw_data)
        return LLMEval.model_validate(data)

    def read_continuous_evals(
        self,
        task_id: str,
        page: int | None = None,
        page_size: int | None = None,
        name: str | None = None,
        llm_eval_name: str | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
    ) -> list[ContinuousEvalResponse]:
        """
        Reads continuous evaluation definitions from the Shield API.

        Args:
            task_id: Task ID to query
            page: Page number for pagination (optional)
            page_size: Number of items per page (optional)
            name: Name filter for continuous eval (optional)
            llm_eval_name: LLM eval name filter (optional)
            created_after: Inclusive start date in ISO8601 format (optional)
            created_before: Exclusive end date in ISO8601 format (optional)

        Returns:
            List of ContinuousEvalResponse objects
        """
        resp = self._cont_evals_client.list_continuous_evals_api_v1_tasks_task_id_continuous_evals_get_with_http_info(
            task_id=task_id,
            page=page,
            page_size=page_size,
            name=name,
            llm_eval_name=llm_eval_name,
            created_after=created_after,
            created_before=created_before,
        )
        data = json.loads(resp.raw_data)
        return [
            ContinuousEvalResponse.model_validate(eval_data)
            for eval_data in data.get("evals", [])
        ]

    def read_transforms(
        self,
        task_id: str,
        page: int | None = None,
        page_size: int | None = None,
        name: str | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
    ) -> list[TraceTransformResponse]:
        """
        Reads transform definitions from the Shield API.

        Args:
            task_id: Task ID to query
            page: Page number for pagination (optional)
            page_size: Number of items per page (optional)
            name: Name filter for transforms using partial matching (optional)
            created_after: Inclusive start date in ISO8601 format (optional)
            created_before: Exclusive end date in ISO8601 format (optional)

        Returns:
            List of TraceTransformResponse objects
        """
        resp = self._transforms_client.list_transforms_for_task_api_v1_tasks_task_id_traces_transforms_get_with_http_info(
            task_id=task_id,
            page=page,
            page_size=page_size,
            name=name,
            created_after=created_after,
            created_before=created_before,
        )
        data = json.loads(resp.raw_data)
        return [
            TraceTransformResponse.model_validate(transform_data)
            for transform_data in data.get("transforms", [])
        ]

    @property
    @abstractmethod
    def shield_external_host(self) -> str:
        raise NotImplementedError


class ShieldConnector(ShieldBaseConnector):
    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        connector_fields = {f.key: f.value for f in connector_config.fields}
        api_key = connector_fields[SHIELD_CONNECTOR_API_KEY_FIELD]
        endpoint = connector_fields[SHIELD_CONNECTOR_ENDPOINT_FIELD]
        self._shield_external_host = endpoint

        super().__init__(
            api_key=api_key,
            endpoint=endpoint,
            connector_config=connector_config,
            logger=logger,
        )

    @property
    def shield_external_host(self) -> str:
        return str(self._shield_external_host)


class EngineInternalConnector(ShieldBaseConnector):
    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        api_key = Config.settings.GENAI_ENGINE_INTERNAL_API_KEY
        endpoint = Config.settings.GENAI_ENGINE_INTERNAL_HOST
        self._shield_external_host = Config.settings.GENAI_ENGINE_INTERNAL_INGRESS_HOST

        if not api_key or not endpoint or not self._shield_external_host:
            raise ValueError(
                "Cannot connect to Shield. Missing environment configurations for "
                "engine internal connection to the Shield API.",
            )

        super().__init__(
            api_key=api_key,
            endpoint=endpoint,
            connector_config=connector_config,
            logger=logger,
        )

    @property
    def shield_external_host(self) -> str:
        return str(self._shield_external_host)
