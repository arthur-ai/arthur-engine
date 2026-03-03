from dataclasses import dataclass
from datetime import datetime, timezone
from logging import Logger
from typing import Any, Optional

import requests
from arthur_client.api_bindings import (
    AvailableDataset,
    ConnectorCheckOutcome,
    ConnectorCheckResult,
    ConnectorSpec,
    DataResultFilter,
    Dataset,
    PutAvailableDatasets,
)
from arthur_common.models.connectors import (
    REST_CONNECTOR_API_KEY_FIELD,
    REST_CONNECTOR_API_KEY_HEADER_FIELD,
    REST_CONNECTOR_AUTHENTICATOR_FIELD,
    REST_CONNECTOR_BASE_URL_FIELD,
    REST_CONNECTOR_BEARER_TOKEN_FIELD,
    REST_CONNECTOR_OAUTH2_CLIENT_ID_FIELD,
    REST_CONNECTOR_OAUTH2_CLIENT_SECRET_FIELD,
    REST_CONNECTOR_OAUTH2_SCOPE_FIELD,
    REST_CONNECTOR_OAUTH2_TOKEN_URL_FIELD,
    REST_DATASET_DATA_PATH_FIELD,
    REST_DATASET_END_TIME_PARAM_FIELD,
    REST_DATASET_ENDPOINT_PATH_FIELD,
    REST_DATASET_HTTP_METHOD_FIELD,
    REST_DATASET_PAGE_PARAM_FIELD,
    REST_DATASET_PAGE_SIZE_PARAM_FIELD,
    REST_DATASET_START_TIME_FORMAT_FIELD,
    REST_DATASET_START_TIME_PARAM_FIELD,
    ConnectorPaginationOptions,
)
from arthur_common.models.enums import (
    RestConnectorAuthenticatorMethods,
    RestConnectorHttpMethod,
)
from pydantic import SecretStr

from connectors.connector import Connector
from tools.connector_read_filters import apply_filters_to_retrieved_inferences

_ISO8601_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_DEFAULT_PAGE_SIZE = 100


@dataclass
class _OAuth2TokenCache:
    access_token: str
    expires_at: datetime

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


class RestConnector(Connector):
    """
    A connector for arbitrary REST API endpoints.

    Supports three authentication methods:
    - API key (via a configurable request header)
    - Bearer token (Authorization header)
    - OAuth2 client credentials (token fetched and cached automatically)

    Time range filtering is user-configurable via dataset locator fields:
    the caller specifies the parameter names, HTTP method (GET/POST), and
    optional timestamp format.
    """

    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        self.logger = logger
        connector_fields = {f.key: f.value for f in connector_config.fields}

        self.base_url: str = connector_fields[REST_CONNECTOR_BASE_URL_FIELD].rstrip("/")
        self.authenticator: str = connector_fields[REST_CONNECTOR_AUTHENTICATOR_FIELD]

        # Auth-specific fields
        api_key = connector_fields.get(REST_CONNECTOR_API_KEY_FIELD)
        self._api_key: Optional[SecretStr] = SecretStr(api_key) if api_key else None
        self._api_key_header: str = connector_fields.get(
            REST_CONNECTOR_API_KEY_HEADER_FIELD,
            "X-API-Key",
        )

        bearer_token = connector_fields.get(REST_CONNECTOR_BEARER_TOKEN_FIELD)
        self._bearer_token: Optional[SecretStr] = (
            SecretStr(bearer_token) if bearer_token else None
        )

        self._oauth2_token_url: Optional[str] = connector_fields.get(
            REST_CONNECTOR_OAUTH2_TOKEN_URL_FIELD,
        )
        self._oauth2_client_id: Optional[str] = connector_fields.get(
            REST_CONNECTOR_OAUTH2_CLIENT_ID_FIELD,
        )
        oauth2_client_secret = connector_fields.get(
            REST_CONNECTOR_OAUTH2_CLIENT_SECRET_FIELD,
        )
        self._oauth2_client_secret: Optional[SecretStr] = (
            SecretStr(oauth2_client_secret) if oauth2_client_secret else None
        )
        self._oauth2_scope: Optional[str] = connector_fields.get(
            REST_CONNECTOR_OAUTH2_SCOPE_FIELD,
        )
        self._oauth2_token_cache: Optional[_OAuth2TokenCache] = None

        self._validate_auth_config()

    def _validate_auth_config(self) -> None:
        match self.authenticator:
            case RestConnectorAuthenticatorMethods.API_KEY:
                if not self._api_key:
                    raise ValueError(
                        f"'{REST_CONNECTOR_API_KEY_FIELD}' must be set for "
                        f"{RestConnectorAuthenticatorMethods.API_KEY} authentication.",
                    )
            case RestConnectorAuthenticatorMethods.BEARER_TOKEN:
                if not self._bearer_token:
                    raise ValueError(
                        f"'{REST_CONNECTOR_BEARER_TOKEN_FIELD}' must be set for "
                        f"{RestConnectorAuthenticatorMethods.BEARER_TOKEN} authentication.",
                    )
            case RestConnectorAuthenticatorMethods.OAUTH2_CLIENT_CREDENTIALS:
                if (
                    not self._oauth2_token_url
                    or not self._oauth2_client_id
                    or not self._oauth2_client_secret
                ):
                    raise ValueError(
                        f"'{REST_CONNECTOR_OAUTH2_TOKEN_URL_FIELD}', "
                        f"'{REST_CONNECTOR_OAUTH2_CLIENT_ID_FIELD}', and "
                        f"'{REST_CONNECTOR_OAUTH2_CLIENT_SECRET_FIELD}' must all be set for "
                        f"{RestConnectorAuthenticatorMethods.OAUTH2_CLIENT_CREDENTIALS} authentication.",
                    )
            case _:
                raise ValueError(
                    f"Authenticator method '{self.authenticator}' is not recognized. "
                    f"Valid methods: {RestConnectorAuthenticatorMethods.values()}",
                )

    def _get_auth_headers(self) -> dict[str, str]:
        match self.authenticator:
            case RestConnectorAuthenticatorMethods.API_KEY:
                return {self._api_key_header: self._api_key.get_secret_value()}  # type: ignore[union-attr]
            case RestConnectorAuthenticatorMethods.BEARER_TOKEN:
                return {"Authorization": f"Bearer {self._bearer_token.get_secret_value()}"}  # type: ignore[union-attr]
            case RestConnectorAuthenticatorMethods.OAUTH2_CLIENT_CREDENTIALS:
                return {"Authorization": f"Bearer {self._get_oauth2_token()}"}
            case _:
                return {}

    def _get_oauth2_token(self) -> str:
        if self._oauth2_token_cache is None or self._oauth2_token_cache.is_expired():
            self._oauth2_token_cache = self._fetch_oauth2_token()
        return self._oauth2_token_cache.access_token

    def _fetch_oauth2_token(self) -> _OAuth2TokenCache:
        payload: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": self._oauth2_client_id or "",
            "client_secret": self._oauth2_client_secret.get_secret_value(),  # type: ignore[union-attr]
        }
        if self._oauth2_scope:
            payload["scope"] = self._oauth2_scope

        response = requests.post(self._oauth2_token_url, data=payload, timeout=30)  # type: ignore[arg-type]
        response.raise_for_status()
        token_data = response.json()

        access_token: str = token_data["access_token"]
        expires_in: int = token_data.get("expires_in", 3600)
        expires_at = datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + expires_in,
            tz=timezone.utc,
        )
        return _OAuth2TokenCache(access_token=access_token, expires_at=expires_at)

    def test_connection(self) -> ConnectorCheckResult:
        try:
            headers = self._get_auth_headers()
            response = requests.get(self.base_url, headers=headers, timeout=30)
            # Any HTTP response (including 4xx) means the endpoint is reachable
            self.logger.info(
                f"REST connector test_connection: {self.base_url} returned {response.status_code}",
            )
        except requests.exceptions.ConnectionError as e:
            self.logger.error("REST connector test_connection failed.", exc_info=e)
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason=f"Connection error: {e}",
            )
        except Exception as e:
            self.logger.error("REST connector test_connection failed.", exc_info=e)
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason=str(e),
            )
        return ConnectorCheckResult(
            connection_check_outcome=ConnectorCheckOutcome.SUCCEEDED,
        )

    def read(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        filters: list[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> list[dict[str, Any]]:
        locator = self._parse_dataset_locator(dataset)
        url = self.base_url + locator["endpoint_path"]
        http_method: str = locator["http_method"]
        start_time_param: str = locator["start_time_param"]
        end_time_param: str = locator["end_time_param"]
        time_format: str = locator.get("start_time_format", _ISO8601_FORMAT)
        data_path: Optional[str] = locator.get("data_path")
        page_param: Optional[str] = locator.get("page_param")
        page_size_param: Optional[str] = locator.get("page_size_param")

        formatted_start = start_time.strftime(time_format)
        formatted_end = end_time.strftime(time_format)

        headers = self._get_auth_headers()
        all_records: list[dict[str, Any]] = []

        page = 1
        # Server-side page size is always fixed; pagination_options controls caller-side slicing only
        server_page_size = _DEFAULT_PAGE_SIZE

        while True:
            time_params = {
                start_time_param: formatted_start,
                end_time_param: formatted_end,
            }
            if page_param:
                time_params[page_param] = str(page)
            if page_size_param:
                time_params[page_size_param] = str(server_page_size)

            if http_method == RestConnectorHttpMethod.GET:
                response = requests.get(
                    url,
                    params=time_params,
                    headers=headers,
                    timeout=60,
                )
            else:
                response = requests.post(
                    url,
                    json=time_params,
                    headers=headers,
                    timeout=60,
                )

            response.raise_for_status()
            records = self._extract_records(response.json(), data_path)

            all_records.extend(records)

            # Stop if not paginating, or if the page is not full (no more data)
            if not page_param or len(records) < server_page_size:
                break
            page += 1

        result = apply_filters_to_retrieved_inferences(all_records, filters)
        assert isinstance(result, list)

        if pagination_options:
            offset, limit = pagination_options.page_params
            start_idx = (offset - 1) * limit
            result = result[start_idx : start_idx + limit]

        return result

    def _parse_dataset_locator(
        self,
        dataset: Dataset | AvailableDataset,
    ) -> dict[str, str]:
        if not dataset.dataset_locator:
            raise ValueError("Dataset must have a dataset_locator configured.")
        locator_fields = {f.key: f.value for f in dataset.dataset_locator.fields}

        endpoint_path = locator_fields.get(REST_DATASET_ENDPOINT_PATH_FIELD, "")
        http_method = locator_fields.get(
            REST_DATASET_HTTP_METHOD_FIELD,
            RestConnectorHttpMethod.GET,
        )
        start_time_param = locator_fields.get(REST_DATASET_START_TIME_PARAM_FIELD)
        end_time_param = locator_fields.get(REST_DATASET_END_TIME_PARAM_FIELD)

        if not start_time_param:
            raise ValueError(
                f"Dataset locator must specify '{REST_DATASET_START_TIME_PARAM_FIELD}'.",
            )
        if not end_time_param:
            raise ValueError(
                f"Dataset locator must specify '{REST_DATASET_END_TIME_PARAM_FIELD}'.",
            )

        result: dict[str, str] = {
            "endpoint_path": f"/{endpoint_path.lstrip('/')}" if endpoint_path else "",
            "http_method": http_method,
            "start_time_param": start_time_param,
            "end_time_param": end_time_param,
        }

        time_format = locator_fields.get(REST_DATASET_START_TIME_FORMAT_FIELD)
        if time_format:
            result["start_time_format"] = time_format

        data_path = locator_fields.get(REST_DATASET_DATA_PATH_FIELD)
        if data_path:
            result["data_path"] = data_path

        page_param = locator_fields.get(REST_DATASET_PAGE_PARAM_FIELD)
        if page_param:
            result["page_param"] = page_param

        page_size_param = locator_fields.get(REST_DATASET_PAGE_SIZE_PARAM_FIELD)
        if page_size_param:
            result["page_size_param"] = page_size_param

        return result

    def _extract_records(
        self,
        response_json: Any,
        data_path: Optional[str],
    ) -> list[dict[str, Any]]:
        if not data_path:
            if isinstance(response_json, list):
                return response_json
            return [response_json] if isinstance(response_json, dict) else []

        data: Any = response_json
        for key in data_path.split("."):
            if not isinstance(data, dict):
                self.logger.warning(
                    f"data_path '{data_path}': expected dict at '{key}', got {type(data).__name__}",
                )
                return []
            data = data.get(key)
            if data is None:
                self.logger.warning(
                    f"data_path '{data_path}': key '{key}' not found in response",
                )
                return []

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        self.logger.warning(
            f"data_path '{data_path}' resolved to non-list/dict type: {type(data).__name__}",
        )
        return []

    def list_datasets(self) -> PutAvailableDatasets:
        raise NotImplementedError(
            "REST connector does not support dataset listing. "
            "Configure the endpoint path directly in the dataset locator.",
        )
