"""
Unit tests for the REST API connector.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from arthur_client.api_bindings import (
    ConnectorCheckOutcome,
    ConnectorFieldDataType,
    ConnectorSpec,
    ConnectorType,
    DataResultFilter,
    DataResultFilterOp,
    Dataset,
    DatasetLocator,
    DatasetLocatorField,
    DatasetSchema,
)
from arthur_common.models.connectors import (
    REST_CONNECTOR_API_KEY_FIELD,
    REST_CONNECTOR_API_KEY_HEADER_FIELD,
    REST_CONNECTOR_AUTHENTICATOR_FIELD,
    REST_CONNECTOR_BASE_URL_FIELD,
    REST_CONNECTOR_BEARER_TOKEN_FIELD,
    REST_CONNECTOR_OAUTH2_CLIENT_ID_FIELD,
    REST_CONNECTOR_OAUTH2_CLIENT_SECRET_FIELD,
    REST_CONNECTOR_OAUTH2_TOKEN_URL_FIELD,
    REST_DATASET_DATA_PATH_FIELD,
    REST_DATASET_END_TIME_PARAM_FIELD,
    REST_DATASET_ENDPOINT_PATH_FIELD,
    REST_DATASET_HTTP_METHOD_FIELD,
    REST_DATASET_PAGE_PARAM_FIELD,
    REST_DATASET_PAGE_SIZE_PARAM_FIELD,
    REST_DATASET_START_TIME_PARAM_FIELD,
    ConnectorPaginationOptions,
)
from arthur_common.models.enums import (
    RestConnectorAuthenticatorMethods,
    RestConnectorHttpMethod,
)

from ml_engine.connectors.rest_connector import RestConnector

_BASE_URL = "https://api.example.com"
_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
_END = datetime(2024, 1, 2, tzinfo=timezone.utc)


def _make_connector_spec(fields: list[dict]) -> ConnectorSpec:
    return ConnectorSpec.model_validate(
        {
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "id": str(uuid4()),
            "connector_type": ConnectorType.REST,
            "name": "Mock REST Connector",
            "temporary": False,
            "fields": fields,
            "last_updated_by_user": None,
            "connector_check_result": None,
            "project_id": str(uuid4()),
            "data_plane_id": str(uuid4()),
        },
    )


def _make_dataset(locator_fields: list[DatasetLocatorField]) -> Dataset:
    return Dataset.model_validate(
        {
            "id": str(uuid4()),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "project_id": str(uuid4()),
            "connector_id": str(uuid4()),
            "dataset_locator": DatasetLocator(fields=locator_fields),
            "data_plane_id": str(uuid4()),
            "model_problem_type": "binary_classification",
            "dataset_schema": DatasetSchema(alias_mask={}, columns=[], column_names={}),
        },
    )


def _api_key_spec(header: str = "X-API-Key") -> ConnectorSpec:
    return _make_connector_spec(
        [
            {
                "key": REST_CONNECTOR_BASE_URL_FIELD,
                "value": _BASE_URL,
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": REST_CONNECTOR_AUTHENTICATOR_FIELD,
                "value": RestConnectorAuthenticatorMethods.API_KEY,
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": REST_CONNECTOR_API_KEY_FIELD,
                "value": "secret-key",
                "is_sensitive": True,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": REST_CONNECTOR_API_KEY_HEADER_FIELD,
                "value": header,
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ],
    )


def _bearer_spec() -> ConnectorSpec:
    return _make_connector_spec(
        [
            {
                "key": REST_CONNECTOR_BASE_URL_FIELD,
                "value": _BASE_URL,
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": REST_CONNECTOR_AUTHENTICATOR_FIELD,
                "value": RestConnectorAuthenticatorMethods.BEARER_TOKEN,
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": REST_CONNECTOR_BEARER_TOKEN_FIELD,
                "value": "my-token",
                "is_sensitive": True,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ],
    )


def _oauth2_spec() -> ConnectorSpec:
    return _make_connector_spec(
        [
            {
                "key": REST_CONNECTOR_BASE_URL_FIELD,
                "value": _BASE_URL,
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": REST_CONNECTOR_AUTHENTICATOR_FIELD,
                "value": RestConnectorAuthenticatorMethods.OAUTH2_CLIENT_CREDENTIALS,
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": REST_CONNECTOR_OAUTH2_TOKEN_URL_FIELD,
                "value": "https://auth.example.com/token",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": REST_CONNECTOR_OAUTH2_CLIENT_ID_FIELD,
                "value": "client-id",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": REST_CONNECTOR_OAUTH2_CLIENT_SECRET_FIELD,
                "value": "client-secret",
                "is_sensitive": True,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ],
    )


def _simple_get_dataset(endpoint: str = "/data") -> Dataset:
    return _make_dataset(
        [
            DatasetLocatorField(key=REST_DATASET_ENDPOINT_PATH_FIELD, value=endpoint),
            DatasetLocatorField(
                key=REST_DATASET_HTTP_METHOD_FIELD,
                value=RestConnectorHttpMethod.GET,
            ),
            DatasetLocatorField(key=REST_DATASET_START_TIME_PARAM_FIELD, value="start"),
            DatasetLocatorField(key=REST_DATASET_END_TIME_PARAM_FIELD, value="end"),
        ],
    )


class TestRestConnectorAuth:
    def test_api_key_header_sent(self):
        spec = _api_key_spec(header="X-Custom-Key")
        connector = RestConnector(spec, Mock())

        mock_response = Mock()
        mock_response.status_code = 200
        with patch("requests.get", return_value=mock_response) as mock_get:
            connector.test_connection()
            _, kwargs = mock_get.call_args
            assert kwargs["headers"].get("X-Custom-Key") == "secret-key"

    def test_api_key_default_header_name(self):
        spec = _make_connector_spec(
            [
                {
                    "key": REST_CONNECTOR_BASE_URL_FIELD,
                    "value": _BASE_URL,
                    "is_sensitive": False,
                    "d_type": ConnectorFieldDataType.STRING.value,
                },
                {
                    "key": REST_CONNECTOR_AUTHENTICATOR_FIELD,
                    "value": RestConnectorAuthenticatorMethods.API_KEY,
                    "is_sensitive": False,
                    "d_type": ConnectorFieldDataType.STRING.value,
                },
                {
                    "key": REST_CONNECTOR_API_KEY_FIELD,
                    "value": "secret-key",
                    "is_sensitive": True,
                    "d_type": ConnectorFieldDataType.STRING.value,
                },
            ],
        )
        connector = RestConnector(spec, Mock())
        mock_response = Mock()
        mock_response.status_code = 200
        with patch("requests.get", return_value=mock_response) as mock_get:
            connector.test_connection()
            _, kwargs = mock_get.call_args
            assert kwargs["headers"].get("X-API-Key") == "secret-key"

    def test_bearer_token_header_sent(self):
        spec = _bearer_spec()
        connector = RestConnector(spec, Mock())

        mock_response = Mock()
        mock_response.status_code = 200
        with patch("requests.get", return_value=mock_response) as mock_get:
            connector.test_connection()
            _, kwargs = mock_get.call_args
            assert kwargs["headers"].get("Authorization") == "Bearer my-token"

    def test_oauth2_token_fetched_and_used(self):
        spec = _oauth2_spec()
        connector = RestConnector(spec, Mock())

        mock_token_response = Mock()
        mock_token_response.json.return_value = {
            "access_token": "fetched-token",
            "expires_in": 3600,
        }

        mock_data_response = Mock()
        mock_data_response.status_code = 200
        mock_data_response.json.return_value = [{"id": "1"}]

        dataset = _simple_get_dataset()

        with patch(
            "requests.post",
            return_value=mock_token_response,
        ) as mock_post, patch(
            "requests.get",
            return_value=mock_data_response,
        ) as mock_get:
            connector.read(dataset, _START, _END)

            # Token endpoint called first
            assert mock_post.call_count == 1
            post_args = mock_post.call_args
            assert post_args[0][0] == "https://auth.example.com/token"
            payload = post_args[1]["data"]
            assert payload["grant_type"] == "client_credentials"
            assert payload["client_id"] == "client-id"
            assert payload["client_secret"] == "client-secret"

            # Data request uses the fetched token
            _, get_kwargs = mock_get.call_args
            assert get_kwargs["headers"].get("Authorization") == "Bearer fetched-token"

    def test_oauth2_token_cached(self):
        spec = _oauth2_spec()
        connector = RestConnector(spec, Mock())

        mock_token_response = Mock()
        mock_token_response.json.return_value = {
            "access_token": "cached-token",
            "expires_in": 3600,
        }

        mock_data_response = Mock()
        mock_data_response.status_code = 200
        mock_data_response.json.return_value = [{"id": "1"}]

        dataset = _simple_get_dataset()

        with patch(
            "requests.post",
            return_value=mock_token_response,
        ) as mock_post, patch("requests.get", return_value=mock_data_response):
            connector.read(dataset, _START, _END)
            connector.read(dataset, _START, _END)
            # Token should only be fetched once
            assert mock_post.call_count == 1

    def test_invalid_authenticator_raises(self):
        spec = _make_connector_spec(
            [
                {
                    "key": REST_CONNECTOR_BASE_URL_FIELD,
                    "value": _BASE_URL,
                    "is_sensitive": False,
                    "d_type": ConnectorFieldDataType.STRING.value,
                },
                {
                    "key": REST_CONNECTOR_AUTHENTICATOR_FIELD,
                    "value": "invalid_method",
                    "is_sensitive": False,
                    "d_type": ConnectorFieldDataType.STRING.value,
                },
            ],
        )
        with pytest.raises(ValueError, match="not recognized"):
            RestConnector(spec, Mock())


class TestRestConnectorRead:
    def test_read_get_passes_time_as_query_params(self):
        spec = _api_key_spec()
        connector = RestConnector(spec, Mock())
        dataset = _simple_get_dataset("/logs")

        mock_response = Mock()
        mock_response.json.return_value = [{"id": "1"}, {"id": "2"}]

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = connector.read(dataset, _START, _END)

        assert len(result) == 2
        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        assert "start" in params
        assert "end" in params
        assert params["start"] == "2024-01-01T00:00:00Z"
        assert params["end"] == "2024-01-02T00:00:00Z"
        assert mock_get.call_args[0][0] == f"{_BASE_URL}/logs"

    def test_read_post_passes_time_in_body(self):
        spec = _api_key_spec()
        connector = RestConnector(spec, Mock())
        dataset = _make_dataset(
            [
                DatasetLocatorField(
                    key=REST_DATASET_ENDPOINT_PATH_FIELD,
                    value="/logs",
                ),
                DatasetLocatorField(
                    key=REST_DATASET_HTTP_METHOD_FIELD,
                    value=RestConnectorHttpMethod.POST,
                ),
                DatasetLocatorField(
                    key=REST_DATASET_START_TIME_PARAM_FIELD,
                    value="from",
                ),
                DatasetLocatorField(key=REST_DATASET_END_TIME_PARAM_FIELD, value="to"),
            ],
        )

        mock_response = Mock()
        mock_response.json.return_value = [{"id": "1"}]

        with patch("requests.post", return_value=mock_response) as mock_post:
            connector.read(dataset, _START, _END)

        _, kwargs = mock_post.call_args
        body = kwargs["json"]
        assert "from" in body
        assert "to" in body
        assert body["from"] == "2024-01-01T00:00:00Z"

    def test_read_extracts_nested_data_path(self):
        spec = _api_key_spec()
        connector = RestConnector(spec, Mock())
        dataset = _make_dataset(
            [
                DatasetLocatorField(
                    key=REST_DATASET_HTTP_METHOD_FIELD,
                    value=RestConnectorHttpMethod.GET,
                ),
                DatasetLocatorField(
                    key=REST_DATASET_START_TIME_PARAM_FIELD,
                    value="start",
                ),
                DatasetLocatorField(key=REST_DATASET_END_TIME_PARAM_FIELD, value="end"),
                DatasetLocatorField(
                    key=REST_DATASET_DATA_PATH_FIELD,
                    value="data.records",
                ),
            ],
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"records": [{"id": "1"}, {"id": "2"}, {"id": "3"}]},
            "total": 3,
        }

        with patch("requests.get", return_value=mock_response):
            result = connector.read(dataset, _START, _END)

        assert len(result) == 3
        assert result[0]["id"] == "1"

    def test_read_flat_list_response_no_data_path(self):
        spec = _bearer_spec()
        connector = RestConnector(spec, Mock())
        dataset = _simple_get_dataset()

        mock_response = Mock()
        mock_response.json.return_value = [{"id": "a"}, {"id": "b"}]

        with patch("requests.get", return_value=mock_response):
            result = connector.read(dataset, _START, _END)

        assert len(result) == 2

    def test_read_pagination_iterates_pages(self):
        spec = _api_key_spec()
        connector = RestConnector(spec, Mock())
        dataset = _make_dataset(
            [
                DatasetLocatorField(
                    key=REST_DATASET_HTTP_METHOD_FIELD,
                    value=RestConnectorHttpMethod.GET,
                ),
                DatasetLocatorField(
                    key=REST_DATASET_START_TIME_PARAM_FIELD,
                    value="start",
                ),
                DatasetLocatorField(key=REST_DATASET_END_TIME_PARAM_FIELD, value="end"),
                DatasetLocatorField(key=REST_DATASET_PAGE_PARAM_FIELD, value="page"),
                DatasetLocatorField(
                    key=REST_DATASET_PAGE_SIZE_PARAM_FIELD,
                    value="page_size",
                ),
            ],
        )

        page1 = [{"id": str(i)} for i in range(100)]
        page2 = [{"id": str(i)} for i in range(100, 110)]

        responses = [Mock(), Mock()]
        responses[0].json.return_value = page1
        responses[1].json.return_value = page2

        with patch("requests.get", side_effect=responses) as mock_get:
            result = connector.read(
                dataset,
                _START,
                _END,
                pagination_options=ConnectorPaginationOptions(page_size=100),
            )

        assert len(result) == 110
        assert mock_get.call_count == 2
        # Second call should have page=2
        _, page2_kwargs = mock_get.call_args
        assert page2_kwargs["params"]["page"] == "2"

    def test_read_stops_paginating_when_empty_page(self):
        spec = _api_key_spec()
        connector = RestConnector(spec, Mock())
        dataset = _make_dataset(
            [
                DatasetLocatorField(
                    key=REST_DATASET_HTTP_METHOD_FIELD,
                    value=RestConnectorHttpMethod.GET,
                ),
                DatasetLocatorField(
                    key=REST_DATASET_START_TIME_PARAM_FIELD,
                    value="start",
                ),
                DatasetLocatorField(key=REST_DATASET_END_TIME_PARAM_FIELD, value="end"),
                DatasetLocatorField(key=REST_DATASET_PAGE_PARAM_FIELD, value="page"),
            ],
        )

        responses = [Mock(), Mock()]
        responses[0].json.return_value = [{"id": "1"}]
        responses[1].json.return_value = []

        with patch("requests.get", side_effect=responses) as mock_get:
            result = connector.read(dataset, _START, _END)

        assert len(result) == 1
        assert mock_get.call_count == 2

    def test_read_applies_filters(self):
        spec = _api_key_spec()
        connector = RestConnector(spec, Mock())
        dataset = _simple_get_dataset()

        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "1", "status": "pass"},
            {"id": "2", "status": "fail"},
            {"id": "3", "status": "pass"},
        ]

        with patch("requests.get", return_value=mock_response):
            result = connector.read(
                dataset,
                _START,
                _END,
                filters=[
                    DataResultFilter(
                        field_name="status",
                        op=DataResultFilterOp.EQUALS,
                        value="pass",
                    ),
                ],
            )

        assert len(result) == 2
        assert all(r["status"] == "pass" for r in result)

    def test_read_applies_pagination_options_offset(self):
        spec = _api_key_spec()
        connector = RestConnector(spec, Mock())
        dataset = _simple_get_dataset()

        mock_response = Mock()
        mock_response.json.return_value = [{"id": str(i)} for i in range(10)]

        with patch("requests.get", return_value=mock_response):
            result = connector.read(
                dataset,
                _START,
                _END,
                pagination_options=ConnectorPaginationOptions(page=2, page_size=3),
            )

        # page=2, page_size=3 → records 3..5
        assert len(result) == 3
        assert result[0]["id"] == "3"

    def test_read_missing_start_time_param_raises(self):
        spec = _api_key_spec()
        connector = RestConnector(spec, Mock())
        dataset = _make_dataset(
            [
                DatasetLocatorField(
                    key=REST_DATASET_HTTP_METHOD_FIELD,
                    value=RestConnectorHttpMethod.GET,
                ),
                DatasetLocatorField(key=REST_DATASET_END_TIME_PARAM_FIELD, value="end"),
            ],
        )

        with pytest.raises(ValueError, match="start_time_param"):
            connector.read(dataset, _START, _END)


class TestRestConnectorTestConnection:
    def test_test_connection_success_on_2xx(self):
        spec = _api_key_spec()
        connector = RestConnector(spec, Mock())

        mock_response = Mock()
        mock_response.status_code = 200
        with patch("requests.get", return_value=mock_response):
            result = connector.test_connection()

        assert result.connection_check_outcome == ConnectorCheckOutcome.SUCCEEDED

    def test_test_connection_success_on_4xx(self):
        # 4xx means endpoint is reachable; not a connection failure
        spec = _bearer_spec()
        connector = RestConnector(spec, Mock())

        mock_response = Mock()
        mock_response.status_code = 403
        with patch("requests.get", return_value=mock_response):
            result = connector.test_connection()

        assert result.connection_check_outcome == ConnectorCheckOutcome.SUCCEEDED

    def test_test_connection_fails_on_connection_error(self):
        import requests as req

        spec = _api_key_spec()
        connector = RestConnector(spec, Mock())

        with patch(
            "requests.get",
            side_effect=req.exceptions.ConnectionError("refused"),
        ):
            result = connector.test_connection()

        assert result.connection_check_outcome == ConnectorCheckOutcome.FAILED
        assert "Connection error" in result.failure_reason

    def test_test_connection_fails_on_unexpected_error(self):
        spec = _bearer_spec()
        connector = RestConnector(spec, Mock())

        with patch("requests.get", side_effect=RuntimeError("unexpected")):
            result = connector.test_connection()

        assert result.connection_check_outcome == ConnectorCheckOutcome.FAILED
        assert result.failure_reason is not None


class TestRestConnectorListDatasets:
    def test_list_datasets_raises_not_implemented(self):
        spec = _api_key_spec()
        connector = RestConnector(spec, Mock())

        with pytest.raises(NotImplementedError):
            connector.list_datasets()
