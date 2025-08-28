import json
from datetime import datetime, timezone
from typing import Dict, List
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from arthur_client.api_bindings import (
    ConnectorFieldDataType,
    ConnectorType,
    DatasetColumn,
    DatasetConnector,
    DatasetLocator,
    DatasetLocatorField,
    DatasetObjectType,
    DatasetScalarType,
    DatasetSchema,
    Definition,
    ObjectValue,
    ScopeSchemaTag,
)
from arthur_common.models.connectors import (
    BIG_QUERY_DATASET_DATASET_ID_FIELD,
    BIG_QUERY_DATASET_TABLE_NAME_FIELD,
    BUCKET_BASED_DATASET_FILE_PREFIX_FIELD,
    BUCKET_BASED_DATASET_FILE_SUFFIX_FIELD,
    BUCKET_BASED_DATASET_FILE_TYPE_FIELD,
    BUCKET_BASED_DATASET_TIMESTAMP_TIME_ZONE_FIELD,
)
from arthur_common.models.datasets import DatasetFileType
from arthur_common.models.enums import ModelProblemType


def mock_bucket_based_connector_spec(
    connector_type: ConnectorType,
    fields: List[Dict],
) -> dict:
    return {
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "id": str(uuid4()),
        "connector_type": connector_type.value,
        "name": f"Mock {connector_type} Spec",
        "temporary": False,
        "fields": fields,
        "last_updated_by_user": None,
        "connector_check_result": None,
        "project_id": str(uuid4()),
        "data_plane_id": str(uuid4()),
    }


def mock_expel_tabular_dataset(locator: DatasetLocator) -> dict:
    return {
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "project_id": str(uuid4()),
        "connector_id": str(uuid4()),
        "dataset_locator": locator,
        "data_plane_id": str(uuid4()),
        "model_problem_type": ModelProblemType.BINARY_CLASSIFICATION.value,
        "dataset_schema": DatasetSchema(
            alias_mask={},
            columns=[
                DatasetColumn(
                    id="6715c83c-7653-4fbd-9bd7-3d1ebc60049b",
                    source_name="expel_alert_id",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id="bccf8f64-8910-4786-8c41-a266fe42c349",
                            dtype="uuid",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="87a7b7d0-a233-4928-a630-b9b209bebb03",
                    source_name="organization_id",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id="d00ea4e8-f664-4343-aad0-28ccc4f58e93",
                            dtype="uuid",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="981a56d2-921e-4d64-9ead-b22b6923a69b",
                    source_name="pred_not_marketing",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id="dbb003d7-8980-4a62-92d5-49835cd4d942",
                            dtype="float",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="3ccc6928-1566-4636-9bfe-b6f3ce465059",
                    source_name="pred_marketing",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id="53cfff8c-d599-4517-abf1-0b92524d9098",
                            dtype="float",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="8107bcae-2738-4cf0-9263-f1863b4be0eb",
                    source_name="predicted_label",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id="71aa954d-edb0-4baa-8a43-282c5e1c688c",
                            dtype="str",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="782fd973-efef-43cb-a3da-f864d9142ea4",
                    source_name="timestamp",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[ScopeSchemaTag.PRIMARY_TIMESTAMP],
                            nullable=False,
                            id="c51e8d04-eaa7-460c-9c39-6eed75d16401",
                            dtype="timestamp",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="893fd973-efef-43cb-a3da-f864d9142ea6",
                    source_name="features",
                    definition=Definition(
                        DatasetObjectType(
                            tag_hints=[],
                            nullable=False,
                            id="d71f8d04-eaa7-460c-9c39-6eed75d16496",
                            object={
                                "severity": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="173c24f3-ab53-4963-ac61-dd32104982a5",
                                        dtype="str",
                                    ),
                                ),
                                "email_colorfulness": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="c0632641-ebac-4441-91f5-6acbf256e790",
                                        dtype="float",
                                    ),
                                ),
                                "domain_age": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="a51d1b33-7751-4ae7-a868-b1c3b7ea3f40",
                                        dtype="float",
                                    ),
                                ),
                                "has_sus_sender_domain": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="364d429f-9368-4d09-9a6f-087431479fcc",
                                        dtype="bool",
                                    ),
                                ),
                                "return_path_match": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="dd8cb56e-ca47-4eec-a324-c73215555467",
                                        dtype="bool",
                                    ),
                                ),
                                "is_personal_domain_sender": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="b44a829a-77b8-4d97-9c38-47ceab64ca76",
                                        dtype="bool",
                                    ),
                                ),
                                "is_bad_corp": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="89f62c4f-d679-4c96-abcc-f4e1a44140b3",
                                        dtype="bool",
                                    ),
                                ),
                                "count_domains": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="53add659-a3cb-45d7-a680-85bac6c283cd",
                                        dtype="int",
                                    ),
                                ),
                                "count_urls": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="da337457-454c-4a8e-ae18-6b71703b0baa",
                                        dtype="int",
                                    ),
                                ),
                                "subject_has_marketing": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="f8ae5b94-ea6c-4939-82ca-7b773bfd1e39",
                                        dtype="bool",
                                    ),
                                ),
                                "sender_has_marketing": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="6e561103-a807-44a5-8659-e69d85873a80",
                                        dtype="bool",
                                    ),
                                ),
                                "body_count_marketing": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="544a59a8-3fb9-4810-8318-1f31a96f1797",
                                        dtype="int",
                                    ),
                                ),
                                "subject_count_marketing": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="a1ea0efc-c751-463c-8748-6014c430cd42",
                                        dtype="int",
                                    ),
                                ),
                                "body_count_malicious": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="664e24d2-0eeb-4688-b3a3-d91c3058abdc",
                                        dtype="int",
                                    ),
                                ),
                                "unsubscribe_ind": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="1223a700-a276-4060-97ab-52f35ebc4c15",
                                        dtype="bool",
                                    ),
                                ),
                                "has_attachments": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="6aba4114-bca1-44d2-9a9b-42ad11dd31d2",
                                        dtype="bool",
                                    ),
                                ),
                                "has_attachment_attack_surface": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="a8e3adc7-ca91-4cf3-a5fd-f635fd0a1672",
                                        dtype="bool",
                                    ),
                                ),
                                "count_attachments": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="b970b28d-1413-4ffe-8130-c354c52a42b4",
                                        dtype="int",
                                    ),
                                ),
                                "len_text_body": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="8048251e-6d26-4656-9f82-16e1b4df7917",
                                        dtype="int",
                                    ),
                                ),
                            },
                        ),
                    ),
                ),
            ],
            column_names={
                "expel_alert_id": "6715c83c-7653-4fbd-9bd7-3d1ebc60049b",
                "organization_id": "87a7b7d0-a233-4928-a630-b9b209bebb03",
                "pred_not_marketing": "981a56d2-921e-4d64-9ead-b22b6923a69b",
                "pred_marketing": "3ccc6928-1566-4636-9bfe-b6f3ce465059",
                "predicted_label": "8107bcae-2738-4cf0-9263-f1863b4be0eb",
                "timestamp": "782fd973-efef-43cb-a3da-f864d9142ea4",
                "features": "893fd973-efef-43cb-a3da-f864d9142ea6",
            },
        ),
    }


def mock_expel_tabular_dataset_no_primary_timestamp_tag(
    locator: DatasetLocator,
) -> dict:
    return {
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "project_id": str(uuid4()),
        "connector_id": str(uuid4()),
        "dataset_locator": locator,
        "data_plane_id": str(uuid4()),
        "model_problem_type": ModelProblemType.BINARY_CLASSIFICATION.value,
        "dataset_schema": DatasetSchema(
            alias_mask={},
            columns=[
                DatasetColumn(
                    id="6715c83c-7653-4fbd-9bd7-3d1ebc60049b",
                    source_name="expel_alert_id",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id="bccf8f64-8910-4786-8c41-a266fe42c349",
                            dtype="uuid",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="87a7b7d0-a233-4928-a630-b9b209bebb03",
                    source_name="organization_id",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id="d00ea4e8-f664-4343-aad0-28ccc4f58e93",
                            dtype="uuid",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="981a56d2-921e-4d64-9ead-b22b6923a69b",
                    source_name="pred_not_marketing",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id="dbb003d7-8980-4a62-92d5-49835cd4d942",
                            dtype="float",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="3ccc6928-1566-4636-9bfe-b6f3ce465059",
                    source_name="pred_marketing",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id="53cfff8c-d599-4517-abf1-0b92524d9098",
                            dtype="float",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="8107bcae-2738-4cf0-9263-f1863b4be0eb",
                    source_name="predicted_label",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id="71aa954d-edb0-4baa-8a43-282c5e1c688c",
                            dtype="str",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="782fd973-efef-43cb-a3da-f864d9142ea4",
                    source_name="timestamp",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id="c51e8d04-eaa7-460c-9c39-6eed75d16401",
                            dtype="timestamp",
                        ),
                    ),
                ),
                DatasetColumn(
                    id="893fd973-efef-43cb-a3da-f864d9142ea6",
                    source_name="features",
                    definition=Definition(
                        DatasetObjectType(
                            tag_hints=[],
                            nullable=False,
                            id="d71f8d04-eaa7-460c-9c39-6eed75d16496",
                            object={
                                "severity": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="173c24f3-ab53-4963-ac61-dd32104982a5",
                                        dtype="str",
                                    ),
                                ),
                                "email_colorfulness": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="c0632641-ebac-4441-91f5-6acbf256e790",
                                        dtype="float",
                                    ),
                                ),
                                "domain_age": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="a51d1b33-7751-4ae7-a868-b1c3b7ea3f40",
                                        dtype="float",
                                    ),
                                ),
                                "has_sus_sender_domain": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="364d429f-9368-4d09-9a6f-087431479fcc",
                                        dtype="bool",
                                    ),
                                ),
                                "return_path_match": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="dd8cb56e-ca47-4eec-a324-c73215555467",
                                        dtype="bool",
                                    ),
                                ),
                                "is_personal_domain_sender": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="b44a829a-77b8-4d97-9c38-47ceab64ca76",
                                        dtype="bool",
                                    ),
                                ),
                                "is_bad_corp": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="89f62c4f-d679-4c96-abcc-f4e1a44140b3",
                                        dtype="bool",
                                    ),
                                ),
                                "count_domains": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="53add659-a3cb-45d7-a680-85bac6c283cd",
                                        dtype="int",
                                    ),
                                ),
                                "count_urls": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="da337457-454c-4a8e-ae18-6b71703b0baa",
                                        dtype="int",
                                    ),
                                ),
                                "subject_has_marketing": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="f8ae5b94-ea6c-4939-82ca-7b773bfd1e39",
                                        dtype="bool",
                                    ),
                                ),
                                "sender_has_marketing": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="6e561103-a807-44a5-8659-e69d85873a80",
                                        dtype="bool",
                                    ),
                                ),
                                "body_count_marketing": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="544a59a8-3fb9-4810-8318-1f31a96f1797",
                                        dtype="int",
                                    ),
                                ),
                                "subject_count_marketing": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="a1ea0efc-c751-463c-8748-6014c430cd42",
                                        dtype="int",
                                    ),
                                ),
                                "body_count_malicious": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="664e24d2-0eeb-4688-b3a3-d91c3058abdc",
                                        dtype="int",
                                    ),
                                ),
                                "unsubscribe_ind": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="1223a700-a276-4060-97ab-52f35ebc4c15",
                                        dtype="bool",
                                    ),
                                ),
                                "has_attachments": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="6aba4114-bca1-44d2-9a9b-42ad11dd31d2",
                                        dtype="bool",
                                    ),
                                ),
                                "has_attachment_attack_surface": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="a8e3adc7-ca91-4cf3-a5fd-f635fd0a1672",
                                        dtype="bool",
                                    ),
                                ),
                                "count_attachments": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="b970b28d-1413-4ffe-8130-c354c52a42b4",
                                        dtype="int",
                                    ),
                                ),
                                "len_text_body": ObjectValue(
                                    DatasetScalarType(
                                        tag_hints=[],
                                        nullable=False,
                                        id="8048251e-6d26-4656-9f82-16e1b4df7917",
                                        dtype="int",
                                    ),
                                ),
                            },
                        ),
                    ),
                ),
            ],
            column_names={
                "expel_alert_id": "6715c83c-7653-4fbd-9bd7-3d1ebc60049b",
                "organization_id": "87a7b7d0-a233-4928-a630-b9b209bebb03",
                "pred_not_marketing": "981a56d2-921e-4d64-9ead-b22b6923a69b",
                "pred_marketing": "3ccc6928-1566-4636-9bfe-b6f3ce465059",
                "predicted_label": "8107bcae-2738-4cf0-9263-f1863b4be0eb",
                "timestamp": "782fd973-efef-43cb-a3da-f864d9142ea4",
                "features": "893fd973-efef-43cb-a3da-f864d9142ea6",
            },
        ),
    }


dataset_locator_happy_path = DatasetLocator(
    fields=[
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_PREFIX_FIELD,
            value="7461c078-cc90-4cad-a590-25c534458dfd/b2f420b8-92ed-425e-9d35-bab014af965e/%Y%m%d",
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_SUFFIX_FIELD,
            value=".json",
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_TYPE_FIELD,
            value=DatasetFileType.JSON,
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_TIMESTAMP_TIME_ZONE_FIELD,
            value="UTC",
        ),
    ],
)

dataset_locator_file_prefix_has_leading_slash = DatasetLocator(
    fields=[
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_PREFIX_FIELD,
            value="/7461c078-cc90-4cad-a590-25c534458dfd/b2f420b8-92ed-425e-9d35-bab014af965e/%Y%m%d/",
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_SUFFIX_FIELD,
            value=".*.json",
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_TYPE_FIELD,
            value=DatasetFileType.JSON,
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_TIMESTAMP_TIME_ZONE_FIELD,
            value="UTC",
        ),
    ],
)

dataset_locator_et_tz = DatasetLocator(
    fields=[
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_PREFIX_FIELD,
            value="7461c078-cc90-4cad-a590-25c534458dfd/b2f420b8-92ed-425e-9d35-bab014af965e/%Y%m%d",
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_SUFFIX_FIELD,
            value=".json",
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_TYPE_FIELD,
            value=DatasetFileType.JSON,
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_TIMESTAMP_TIME_ZONE_FIELD,
            value="US/Eastern",
        ),
    ],
)

dataset_locator_file_prefix_without_small_enough_partition = DatasetLocator(
    fields=[
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_PREFIX_FIELD,
            value="7461c078-cc90-4cad-a590-25c534458dfd/b2f420b8-92ed-425e-9d35-bab014af965e/%Y%m",
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_SUFFIX_FIELD,
            value=".json",
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_FILE_TYPE_FIELD,
            value=DatasetFileType.JSON,
        ),
        DatasetLocatorField(
            key=BUCKET_BASED_DATASET_TIMESTAMP_TIME_ZONE_FIELD,
            value="UTC",
        ),
    ],
)


@pytest.fixture
def mock_bigquery_client():
    with patch("google.cloud.bigquery.Client") as mock_client, patch(
        "google.oauth2.service_account.Credentials.from_service_account_info",
    ) as mock_creds:
        mock_creds.return_value = Mock()
        yield mock_client.return_value


MOCK_BQ_CONNECTOR_SPEC = {
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "id": str(uuid4()),
    "connector_type": ConnectorType.BIGQUERY.value,
    "name": "Mock Big Query Connector Spec",
    "temporary": False,
    "fields": [
        {
            "key": "project_id",
            "value": "my_project_id",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "credentials",
            "value": json.dumps(
                {
                    "type": "service_account",
                    "project_id": "my_project_id",
                    "private_key_id": "mock_private_key_id",
                    "private_key": "-----BEGIN PRIVATE KEY-----\nMOCK_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
                    "client_email": "mock-service-account@my-project.iam.gserviceaccount.com",
                    "client_id": "123456789",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                },
            ),
            "is_sensitive": True,
            "d_type": ConnectorFieldDataType.DICT.value,
        },
    ],
    "last_updated_by_user": None,
    "connector_check_result": None,
    "project_id": str(uuid4()),
    "data_plane_id": str(uuid4()),
}
MOCK_BQ_DATASET = {
    "id": str(uuid4()),
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "project_id": str(uuid4()),
    "connector": DatasetConnector(
        id=str(uuid4()),
        name="Mock BigQuery Connector",
        connector_type=ConnectorType.BIGQUERY,
    ),
    "data_plane_id": str(uuid4()),
    "dataset_locator": DatasetLocator(
        fields=[
            DatasetLocatorField(
                key=BIG_QUERY_DATASET_TABLE_NAME_FIELD,
                value="test_table",
            ),
            DatasetLocatorField(
                key=BIG_QUERY_DATASET_DATASET_ID_FIELD,
                value="test_dataset",
            ),
        ],
    ),
    "model_problem_type": ModelProblemType.BINARY_CLASSIFICATION.value,
    "dataset_schema": DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id="6715c83c-7653-4fbd-9bd7-3d1ebc60049b",
                source_name="id",
                definition=Definition(
                    DatasetScalarType(
                        tag_hints=[],
                        nullable=False,
                        id="bccf8f64-8910-4786-8c41-a266fe42c349",
                        dtype="uuid",
                    ),
                ),
            ),
            DatasetColumn(
                id="981a56d2-921e-4d64-9ead-b22b6923a69b",
                source_name="name",
                definition=Definition(
                    DatasetScalarType(
                        tag_hints=[],
                        nullable=False,
                        id="dbb003d7-8980-4a62-92d5-49835cd4d942",
                        dtype="str",
                    ),
                ),
            ),
            DatasetColumn(
                id="782fd973-efef-43cb-a3da-f864d9142ea4",
                source_name="timestamp",
                definition=Definition(
                    DatasetScalarType(
                        tag_hints=[ScopeSchemaTag.PRIMARY_TIMESTAMP],
                        nullable=False,
                        id="c51e8d04-eaa7-460c-9c39-6eed75d16401",
                        dtype="timestamp",
                    ),
                ),
            ),
            DatasetColumn(
                id="882fd973-efef-43cb-a3da-f864d9142ea4",
                source_name="description",
                definition=Definition(
                    DatasetScalarType(
                        tag_hints=[],
                        nullable=False,
                        id="d51e8d04-eaa7-460c-9c39-6eed75d16401",
                        dtype="str",
                    ),
                ),
            ),
            DatasetColumn(
                id="982fd973-efef-43cb-a3da-f864d9142ea4",
                source_name="desc2",
                definition=Definition(
                    DatasetScalarType(
                        tag_hints=[],
                        nullable=False,
                        id="e51e8d04-eaa7-460c-9c39-6eed75d16401",
                        dtype="str",
                    ),
                ),
            ),
            DatasetColumn(
                id="182fd973-efef-43cb-a3da-f864d9142ea4",
                source_name="numeric_col",
                definition=Definition(
                    DatasetScalarType(
                        tag_hints=[],
                        nullable=False,
                        id="a51e8d04-eaa7-460c-9c39-6eed75d16401",
                        dtype="int",
                    ),
                ),
            ),
        ],
        column_names={
            "6715c83c-7653-4fbd-9bd7-3d1ebc60049b": "id",
            "981a56d2-921e-4d64-9ead-b22b6923a69b": "name",
            "782fd973-efef-43cb-a3da-f864d9142ea4": "timestamp",
            "882fd973-efef-43cb-a3da-f864d9142ea4": "description",
            "982fd973-efef-43cb-a3da-f864d9142ea4": "desc2",
            "182fd973-efef-43cb-a3da-f864d9142ea4": "numeric_col",
        },
    ),
}
