import json
import logging
import math
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib import parse
from uuid import uuid4

import pytest
import urllib3
from arthur_client.api_bindings import (
    AvailableDataset,
    ConnectorFieldDataType,
    ConnectorSpec,
    ConnectorType,
    DataResultFilter,
    DataResultFilterOp,
    DatasetLocator,
    DatasetLocatorField,
)
from arthur_common.models.connectors import ConnectorPaginationOptions
from arthur_common.models.enums import ModelProblemType
from arthur_common.models.request_schemas import NewRuleRequest
from config.config import Config
from connectors.shield_connector import (
    EngineInternalConnector,
    ShieldBaseConnector,
    ShieldConnector,
)
from tools.agentic_filters import SHIELD_SORT_DESC, SHIELD_SORT_FILTER

logger = logging.getLogger("job_logger")

MOCK_SHIELD_HOST = "http://localhost:45678"
MOCK_SHIELD_API_KEY = "1234567890"


class Urllib3Mock:
    def __init__(self):
        self._responses: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
        self._called_urls: List[tuple[str, str]] = []

    def _parse_url(self, url: str) -> tuple[str, Dict[str, List[str]]]:
        """Parse a URL into its base path and query parameters."""
        parsed = parse.urlparse(url)
        query_params = parse.parse_qs(parsed.query)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return base_url, query_params

    def _urls_match(self, url1: str, url2: str) -> bool:
        """Compare two URLs, ignoring query parameter order."""
        base1, params1 = self._parse_url(url1)
        base2, params2 = self._parse_url(url2)

        # Compare base URLs
        if base1 != base2:
            return False

        # Compare query parameters
        if set(params1.keys()) != set(params2.keys()):
            return False

        for key in params1:
            # Sort lists to handle order-independent comparison
            if sorted(params1[key]) != sorted(params2[key]):
                return False

        return True

    def add_response(
        self,
        url: str,
        text: str,
        method: str = "GET",
        status: int = 200,
    ) -> None:
        """Add a mock response for a given URL.

        Args:
            url: The URL to mock
            text: The response text
            method: The HTTP method (default: GET)
            status: The HTTP status code (default: 200)
        """
        key = (url, method.upper())
        if key not in self._responses:
            self._responses[key] = []
        self._responses[key].append({"text": text, "status": status})

    def get_response(self, url: str, method: str) -> Optional[Dict[str, Any]]:
        """Get the mock response for a given URL and method.
        Returns responses in FIFO order."""
        self._called_urls.append((url, method.upper()))

        # Find matching response by comparing URLs and methods
        for (mock_url, mock_method), responses in self._responses.items():
            if self._urls_match(mock_url, url) and mock_method == method.upper():
                if not responses:
                    return None
                return responses.pop(0)

        return None

    def assert_all_responses_called(self) -> None:
        """Assert that all registered responses were called."""
        uncalled = []
        for (mock_url, mock_method), responses in self._responses.items():
            if responses:  # Only check if there are responses left
                uncalled.append(
                    f"{mock_method} {mock_url} ({len(responses)} responses remaining)",
                )

        if uncalled:
            raise AssertionError(f"Uncalled mock responses for: {uncalled}")

    def reset(self) -> None:
        """Reset the mock state."""
        self._responses.clear()
        self._called_urls.clear()


@pytest.fixture
def urllib3_mock(monkeypatch):
    mock = Urllib3Mock()

    def mock_request(self, method, url, **kwargs):
        response = mock.get_response(url, method)
        if response is None:
            raise urllib3.exceptions.HTTPError(
                f"No mock response found for {method} {url}",
            )

        # Create a mock response object that mimics urllib3's HTTPResponse
        class MockResponse:
            def __init__(self, data):
                self._content = data["text"].encode()
                self.status = data["status"]
                self.reason = "OK" if data["status"] == 200 else "Error"
                self.headers = {"content-type": "application/json"}
                self.data = self._content

            def read(self):
                return self._content

            @property
            def raw_data(self):
                return self._content.decode()

        return MockResponse(response)

    # Patch the PoolManager's request method
    monkeypatch.setattr(urllib3.PoolManager, "request", mock_request)
    return mock


def mock_shield_connector_spec(host: str) -> dict[str, Any]:
    return {
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "id": str(uuid4()),
        "connector_type": ConnectorType.SHIELD.value,
        "name": "Mock Shield Connector Spec",
        "temporary": False,
        "fields": [
            {
                "key": "endpoint",
                "value": host,
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "api_key",
                "value": MOCK_SHIELD_API_KEY,
                "is_sensitive": True,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ],
        "last_updated_by_user": None,
        "connector_check_result": None,
        "project_id": str(uuid4()),
        "data_plane_id": str(uuid4()),
    }


def mock_engine_internal_connector_spec() -> dict[str, Any]:
    Config.settings.GENAI_ENGINE_INTERNAL_API_KEY = MOCK_SHIELD_API_KEY
    Config.settings.GENAI_ENGINE_INTERNAL_HOST = MOCK_SHIELD_HOST
    Config.settings.GENAI_ENGINE_INTERNAL_INGRESS_HOST = MOCK_SHIELD_HOST
    return {
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "id": str(uuid4()),
        "connector_type": ConnectorType.ENGINE_INTERNAL.value,
        "name": "Mock Engine Internal Connector Spec",
        "temporary": False,
        "fields": [],
        "last_updated_by_user": None,
        "connector_check_result": None,
        "project_id": str(uuid4()),
        "data_plane_id": str(uuid4()),
    }


MOCK_SHIELD_TASK_ID = str(uuid4())

MOCK_SHIELD_AVAILABLE_DATASET = {
    "id": str(uuid4()),
    "dataset_locator": DatasetLocator(
        fields=[
            DatasetLocatorField(
                key="task_id",
                value=MOCK_SHIELD_TASK_ID,
            ),
        ],
    ),
    "connector_id": mock_shield_connector_spec(MOCK_SHIELD_HOST)["id"],
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "project_id": mock_shield_connector_spec(MOCK_SHIELD_HOST)["project_id"],
    "data_plane_id": mock_shield_connector_spec(MOCK_SHIELD_HOST)["data_plane_id"],
}


def inference_generator(id: str):
    return {
        "id": str(uuid.uuid4()),
        "inference_id": id,
        "result": "Pass",
        "created_at": int(datetime.now(timezone.utc).timestamp()),
        "updated_at": int(datetime.now(timezone.utc).timestamp()),
        "inference_prompt": {
            "id": str(uuid.uuid4()),
            "inference_id": id,
            "result": "Pass",
            "message": "This is the inference prompt",
            "prompt_rule_results": [],
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "updated_at": int(datetime.now(timezone.utc).timestamp()),
        },
        "inference_response": {
            "message": "This is the inference response",
            "context": "This is the inference context",
            "id": str(uuid.uuid4()),
            "inference_id": id,
            "result": "Pass",
            "response_rule_results": [],
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "updated_at": int(datetime.now(timezone.utc).timestamp()),
        },
        "inference_feedback": [],
    }


def response_generator(total_infs: int, page: int, page_size: int):
    inferences_left_to_show = total_infs - (page * page_size)
    return {
        "count": total_infs,
        "inferences": [
            inference_generator(str(page * page_size + i))
            for i in range(min(inferences_left_to_show, page_size))
        ],
    }


def mock_shield_data(
    urllib3_mock: Urllib3Mock,
    total_count_inf: int,
    start_time: datetime,
    end_time: datetime,
    page: int | None = None,
    page_size: int = 10,
    limit: int | None = None,
    **params,
):
    """
    This function will mock out the expected shield calls for a given amount of inferences between a start and
    end timestamp.
    If `page` is set, it will only mock the call to that single page.
    """
    if limit is not None:
        # set the exp num pages based on limit
        expect_num_pages = math.ceil(limit / page_size)
    else:
        # If the total number of inferences is a multiple of the page size, we need to mock an extra page that the connector will use to determine when to break the read loop
        expect_num_pages = 1 if total_count_inf % page_size == 0 else 0
        # set the exp num pages based on how many it will take to fetch all
        expect_num_pages += math.ceil(total_count_inf / page_size)

    pages_to_mock = [page] if page is not None else list(range(expect_num_pages))
    base_url = f"{MOCK_SHIELD_HOST}/api/v2/inferences/query?"

    for page_to_mock in pages_to_mock:
        query_params = {
            "include_count": "false",
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "page": page_to_mock,
            "page_size": page_size,
            **params,
        }

        urllib3_mock.add_response(
            url=f"{base_url}{parse.urlencode(query_params, doseq=True)}",
            text=json.dumps(
                response_generator(total_count_inf, page_to_mock, page_size),
            ),
            method="GET",
            status=200,
        )


@pytest.mark.parametrize(
    "connector_params,connector_pagination_params,expected_params,expected_total_rows",
    [
        # default case, should read all 5400 inferences for the task in descending order
        (
            {},
            None,
            {
                "page_size": 1500,
                "task_ids": MOCK_SHIELD_TASK_ID,
                SHIELD_SORT_FILTER: SHIELD_SORT_DESC,
            },
            5400,
        ),
        # only set a limit
        (
            {},
            ConnectorPaginationOptions(page_size=75),
            {
                "page_size": 75,
                "limit": 75,
                "task_ids": MOCK_SHIELD_TASK_ID,
                SHIELD_SORT_FILTER: SHIELD_SORT_DESC,
            },
            75,
        ),
        # requesting a specific page, should only fetch default page size as defined by the pagination contract
        (
            {},
            ConnectorPaginationOptions(page=1),
            {
                "page_size": 25,
                "page": 0,
                "task_ids": MOCK_SHIELD_TASK_ID,
                SHIELD_SORT_FILTER: SHIELD_SORT_DESC,
            },
            25,
        ),
        # requesting a specific page & page size, should only fetch page size argument number of inferences
        (
            {},
            ConnectorPaginationOptions(page=2, page_size=50),
            {
                "page": 1,
                "page_size": 50,
                "task_ids": MOCK_SHIELD_TASK_ID,
                SHIELD_SORT_FILTER: SHIELD_SORT_DESC,
            },
            50,
        ),
        # other filters, the mock does not change the response
        # based on the filters, but asserts they make the URL params
        (
            {
                "conversation_id": "some ID",
                "inference_id": "some ID",
                "user_id": "some ID",
                "rule_types": ["KeywordRule", "ModelHallucinationRuleV2"],
                "rule_statuses": ["Pass", "Fail"],
                "prompt_statuses": ["Pass", "Fail"],
                "response_statuses": ["Pass", "Fail"],
                SHIELD_SORT_FILTER: "asc",
            },
            None,
            {
                "conversation_id": "some ID",
                "inference_id": "some ID",
                "user_id": "some ID",
                "rule_types": ["KeywordRule", "ModelHallucinationRuleV2"],
                "rule_statuses": ["Pass", "Fail"],
                "prompt_statuses": ["Pass", "Fail"],
                "response_statuses": ["Pass", "Fail"],
                SHIELD_SORT_FILTER: "asc",
                "page_size": 1500,
                "task_ids": MOCK_SHIELD_TASK_ID,
            },
            5400,
        ),
    ],
)
def test_shield_read_data(
    urllib3_mock: Urllib3Mock,
    connector_params,
    connector_pagination_params,
    expected_params,
    expected_total_rows,
) -> None:
    end_timestamp = datetime.now(timezone.utc)
    start_timestamp = end_timestamp - timedelta(days=30)
    avail_dataset = AvailableDataset.model_validate(MOCK_SHIELD_AVAILABLE_DATASET)
    spec = ConnectorSpec.model_validate(mock_shield_connector_spec(MOCK_SHIELD_HOST))
    conn = ShieldConnector(spec, logger)

    # mock expected responses
    mock_shield_data(
        urllib3_mock,
        5400,
        start_timestamp,
        end_timestamp,
        **expected_params,
    )

    filters = [
        DataResultFilter(field_name=k, op="equals", value=v)
        for k, v in connector_params.items()
    ]
    rows = conn.read(
        avail_dataset,
        start_time=start_timestamp,
        end_time=end_timestamp,
        filters=filters,
        pagination_options=connector_pagination_params,
    )
    assert len(rows) == expected_total_rows
    urllib3_mock.assert_all_responses_called()


@pytest.mark.parametrize(
    "host,should_err,expected_url",
    [
        ("://localhost:45678", True, None),  # missing scheme
        ("http://:45678", True, None),  # missing host
        ("http://localhost", False, "http://localhost"),  # missing port - valid
        ("http://localhost:45678", False, "http://localhost:45678"),  # valid url
    ],
)
def test_validate_host(host, should_err, expected_url) -> None:
    spec = ConnectorSpec.model_validate(mock_shield_connector_spec(host))
    if should_err:
        with pytest.raises(ValueError) as exc:
            ShieldConnector(spec, logger)
            assert "Endpoint does not include" in exc.value
    else:
        conn = ShieldConnector(spec, logger)
        assert str(conn._genai_client.configuration.host) == expected_url


@pytest.mark.parametrize(
    "conn",
    [
        ShieldConnector(
            ConnectorSpec.model_validate(mock_shield_connector_spec(MOCK_SHIELD_HOST)),
            logger,
        ),
        EngineInternalConnector(
            ConnectorSpec.model_validate(mock_engine_internal_connector_spec()),
            logger,
        ),
    ],
)
def test_shield_task_and_rule_management(
    conn: ShieldBaseConnector,
    urllib3_mock: Urllib3Mock,
) -> None:
    """Test the task and rule management functionality of the Shield connector."""
    # Mock task creation response
    task_id = str(uuid4())
    task_name = "Test Task"
    urllib3_mock.add_response(
        url=f"{MOCK_SHIELD_HOST}/api/v2/tasks",
        text=json.dumps(
            {
                "id": task_id,
                "name": task_name,
                "created_at": int(datetime.now(timezone.utc).timestamp()),
                "updated_at": int(datetime.now(timezone.utc).timestamp()),
                "rules": [],
                "is_agentic": True,
            },
        ),
        method="POST",
        status=200,
    )

    # Create task
    task = conn.create_task(task_name)
    assert task.id == task_id
    assert task.name == task_name

    # Mock task validation key creation response
    task_validation_key_id = str(uuid4())
    urllib3_mock.add_response(
        url=f"{MOCK_SHIELD_HOST}/auth/api_keys/",
        text=json.dumps(
            {
                "id": task_validation_key_id,
                "key": "ABCDEFG",
                "description": "Task Validation Key",
                "is_active": True,
                "created_at": int(datetime.now(timezone.utc).timestamp()),
                "deactivated_at": None,
                "message": None,
            },
        ),
        method="POST",
        status=200,
    )

    api_key_resp = conn.create_task_validation_key(task.id)
    assert api_key_resp.id == task_validation_key_id

    # Mock task validation key deletion response
    urllib3_mock.add_response(
        url=f"{MOCK_SHIELD_HOST}/auth/api_keys/deactivate/{task_validation_key_id}",
        text=json.dumps(
            {
                "id": task_validation_key_id,
                "key": "ABCDEFG",
                "description": "Task Validation Key",
                "is_active": True,
                "created_at": int(datetime.now(timezone.utc).timestamp()),
                "deactivated_at": int(datetime.now(timezone.utc).timestamp()),
                "message": None,
            },
        ),
        method="DELETE",
        status=204,
    )

    conn.delete_task_validation_key(task_validation_key_id)

    # Mock rule creation responses
    mocked_rules = [
        {
            "id": str(uuid4()),
            "name": "Rule 1",
            "enabled": True,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "updated_at": int(datetime.now(timezone.utc).timestamp()),
            "type": "KeywordRule",
            "scope": "task",
            "apply_to_prompt": True,
            "apply_to_response": True,
            "config": {
                "keywords": ["keyword1", "keyword2"],
            },
        },
        {
            "id": str(uuid4()),
            "name": "Rule 2",
            "enabled": True,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "updated_at": int(datetime.now(timezone.utc).timestamp()),
            "type": "RegexRule",
            "scope": "task",
            "apply_to_prompt": True,
            "apply_to_response": True,
            "config": {
                "regex_patterns": [".*"],
            },
        },
        {
            "id": str(uuid4()),
            "name": "Rule 3",
            "enabled": True,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "updated_at": int(datetime.now(timezone.utc).timestamp()),
            "type": "ToxicityRule",
            "scope": "task",
            "apply_to_prompt": True,
            "apply_to_response": True,
            "config": {
                "threshold": 0.5,
            },
        },
    ]

    mocked_task = {
        "id": str(uuid4()),
        "name": task_name,
        "created_at": int(datetime.now(timezone.utc).timestamp()),
        "updated_at": int(datetime.now(timezone.utc).timestamp()),
        "rules": mocked_rules,
        "is_agentic": True,
    }

    # mock requests to create the rules
    for rule in mocked_rules:
        urllib3_mock.add_response(
            url=f"{MOCK_SHIELD_HOST}/api/v2/tasks/{task_id}/rules",
            text=json.dumps(rule),
            method="POST",
            status=200,
        )

    # Add rules to task
    rules = []
    for rule in mocked_rules:
        # shield's API models use "before" validations which modify the source object, copy
        # before passing into model_validate
        new_rule = NewRuleRequest.model_validate(deepcopy(rule))
        rule_resp = conn.add_rule_to_task(task_id, new_rule)
        rules.append(rule_resp)
        assert rule_resp.name == rule["name"]
        assert rule_resp.enabled is True

    # Mock rule enable/disable responses
    disabled_rule_json = mocked_rules[0]
    disabled_rule_json["enabled"] = False
    urllib3_mock.add_response(
        url=f"{MOCK_SHIELD_HOST}/api/v2/tasks/{task_id}/rules/{rules[0].id}",
        text=json.dumps(mocked_task),
        method="PATCH",
        status=200,
    )

    # Disable first rule
    conn.disable_task_rule(task_id, mocked_rules[0]["id"])

    # re-enable first rule, mock the request
    urllib3_mock.add_response(
        url=f"{MOCK_SHIELD_HOST}/api/v2/tasks/{task_id}/rules/{mocked_rules[0]['id']}",
        text=json.dumps(mocked_task),
        method="PATCH",
        status=200,
    )

    conn.enable_task_rule(task_id, mocked_rules[0]["id"])

    # Mock rule deletion response
    urllib3_mock.add_response(
        url=f"{MOCK_SHIELD_HOST}/api/v2/tasks/{task_id}/rules/{mocked_rules[2]['id']}",
        text="",
        method="DELETE",
        status=204,
    )

    # Delete third rule
    conn.delete_task_rule(task_id, mocked_rules[2]["id"])

    # Mock task deletion response
    urllib3_mock.add_response(
        url=f"{MOCK_SHIELD_HOST}/api/v2/tasks/{task_id}",
        text="",
        method="DELETE",
        status=204,
    )

    # Delete task
    conn.delete_task(task_id)

    # Verify all mocked responses were called
    urllib3_mock.assert_all_responses_called()


def test_agentic_dataset_parameter_conversion_integration(urllib3_mock: Urllib3Mock):
    """Test end-to-end parameter conversion for agentic datasets in the connector."""
    end_timestamp = datetime.now(timezone.utc)
    start_timestamp = end_timestamp - timedelta(days=1)

    # Create agentic dataset
    agentic_dataset = AvailableDataset.model_validate(
        {
            **MOCK_SHIELD_AVAILABLE_DATASET,
            "model_problem_type": ModelProblemType.AGENTIC_TRACE.value,
        },
    )

    spec = ConnectorSpec.model_validate(mock_shield_connector_spec(MOCK_SHIELD_HOST))
    conn = ShieldConnector(spec, logger)

    # Mock the traces endpoint - we'll verify the parameters in the URL
    expected_params = {
        "task_ids": MOCK_SHIELD_TASK_ID,
        "start_time": start_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
        "end_time": end_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
        "page": "0",
        "page_size": "1500",
        "query_relevance_gt": "0.5",
        "tool_name": "search_tool",
        "sort": "desc",
    }

    expected_url = f"{MOCK_SHIELD_HOST}/v1/traces/query?" + parse.urlencode(
        expected_params,
        doseq=True,
    )

    urllib3_mock.add_response(
        url=expected_url,
        text=json.dumps({"count": 0, "traces": []}),
        method="GET",
        status=200,
    )

    # Test with agentic filters that should be converted to proper parameters
    filters = [
        DataResultFilter(
            field_name="query_relevance",
            op=DataResultFilterOp.GREATER_THAN,
            value=0.5,
        ),
        DataResultFilter(
            field_name="tool_name",
            op=DataResultFilterOp.EQUALS,
            value="search_tool",
        ),
    ]

    rows = conn.read(
        agentic_dataset,
        start_time=start_timestamp,
        end_time=end_timestamp,
        filters=filters,
    )

    # Should successfully make the call without errors
    urllib3_mock.assert_all_responses_called()


def test_agentic_dataset_validation_error_handling(urllib3_mock: Urllib3Mock):
    """Test that agentic dataset validation errors are properly handled."""
    end_timestamp = datetime.now(timezone.utc)
    start_timestamp = end_timestamp - timedelta(days=1)

    agentic_dataset = AvailableDataset.model_validate(
        {
            **MOCK_SHIELD_AVAILABLE_DATASET,
            "model_problem_type": ModelProblemType.AGENTIC_TRACE.value,
        },
    )

    spec = ConnectorSpec.model_validate(mock_shield_connector_spec(MOCK_SHIELD_HOST))
    conn = ShieldConnector(spec, logger)

    # Invalid filters (relevance > 1.0)
    filters = [
        DataResultFilter(
            field_name="query_relevance",
            op=DataResultFilterOp.GREATER_THAN,
            value=1.5,  # Invalid: above maximum
        ),
    ]

    with pytest.raises(ValueError) as exc_info:
        conn.read(
            agentic_dataset,
            start_time=start_timestamp,
            end_time=end_timestamp,
            filters=filters,
        )

    assert "Invalid trace query filters" in str(exc_info.value)


@pytest.mark.parametrize(
    "connector_params,expected_params",
    [
        # Test various agentic filter types get converted correctly
        (
            {
                "query_relevance": (DataResultFilterOp.GREATER_THAN, 0.6),
                "response_relevance": (DataResultFilterOp.LESS_THAN_OR_EQUAL, 0.8),
                "tool_name": (DataResultFilterOp.EQUALS, "calculator"),
            },
            {
                "query_relevance_gt": "0.6",
                "response_relevance_lte": "0.8",
                "tool_name": "calculator",
            },
        ),
        (
            {
                "trace_duration": (DataResultFilterOp.GREATER_THAN_OR_EQUAL, 1500),
                "span_types": (DataResultFilterOp.IN, ["LLM", "CHAIN"]),
            },
            {
                "trace_duration_gte": "1500",
                "span_types": ["LLM", "CHAIN"],
            },
        ),
    ],
)
def test_agentic_dataset_filter_parameter_mapping(
    urllib3_mock: Urllib3Mock,
    connector_params,
    expected_params,
):
    """Test that agentic filter parameters are correctly mapped in connector calls."""
    end_timestamp = datetime.now(timezone.utc)
    start_timestamp = end_timestamp - timedelta(days=1)

    agentic_dataset = AvailableDataset.model_validate(
        {
            **MOCK_SHIELD_AVAILABLE_DATASET,
            "model_problem_type": ModelProblemType.AGENTIC_TRACE.value,
        },
    )

    spec = ConnectorSpec.model_validate(mock_shield_connector_spec(MOCK_SHIELD_HOST))
    conn = ShieldConnector(spec, logger)

    # Build base parameters
    base_params = {
        "task_ids": MOCK_SHIELD_TASK_ID,
        "start_time": start_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
        "end_time": end_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
        "page": "0",
        "page_size": "1500",
        "sort": "desc",
    }

    # Add expected parameters
    all_params = {**base_params, **expected_params}
    expected_url = f"{MOCK_SHIELD_HOST}/v1/traces/query?" + parse.urlencode(
        all_params,
        doseq=True,
    )

    urllib3_mock.add_response(
        url=expected_url,
        text=json.dumps({"count": 0, "traces": []}),
        method="GET",
        status=200,
    )

    # Convert connector_params to filters
    filters = [
        DataResultFilter(field_name=field, op=op, value=value)
        for field, (op, value) in connector_params.items()
    ]

    # This should successfully make the call with correct parameter conversion
    conn.read(
        agentic_dataset,
        start_time=start_timestamp,
        end_time=end_timestamp,
        filters=filters,
    )

    # Verify the correct URL was called
    urllib3_mock.assert_all_responses_called()
