from typing import Union

from arthur_client.api_bindings import DatasetColumn
from arthur_client.api_bindings import DatasetListType
from arthur_client.api_bindings import DatasetListType as ClientDatasetListType
from arthur_client.api_bindings import DatasetObjectType
from arthur_client.api_bindings import DatasetObjectType as ClientDatasetObjectType
from arthur_client.api_bindings import DatasetScalarType
from arthur_client.api_bindings import DatasetScalarType as ClientDatasetScalarType
from arthur_client.api_bindings import DatasetSchema as ClientDatasetSchema
from arthur_client.api_bindings import Definition
from arthur_client.api_bindings import Definition as ClientDefinition
from arthur_client.api_bindings import Items, ObjectValue
from arthur_client.api_bindings import PutDatasetSchema as ClientPutDatasetSchema
from arthur_common.models.schema_definitions import (
    DatasetColumn as InternalDatasetColumn,
)
from arthur_common.models.schema_definitions import (
    DatasetListType as InternalDatasetListType,
)
from arthur_common.models.schema_definitions import (
    DatasetObjectType as InternalDatasetObjectType,
)
from arthur_common.models.schema_definitions import (
    DatasetScalarType as InternalDatasetScalarType,
)
from arthur_common.models.schema_definitions import (
    DatasetSchema as InternalDatasetSchema,
)
from arthur_common.models.schema_definitions import (
    DatasetSchemaTypeUnion as InternalDatasetSchemaTypeUnion,
)

r"""
                  ."`".
              .-./ _=_ \.-.
             {  (,(oYo),) }}
             {{ |   "   |} }
             { { \(---)/  }}
             {{  }'-=-'{ } }
             { { }._:_.{  }}
             {{  } -:- { } }
             {_{ }`===`{  _}
            ((((\)     (/))))

Why did the gorilla write this converter library? Because he was tired of monkeying around with incompatible schemas!
"""


def client_to_common_dataset_schema(
    schema: ClientDatasetSchema,
) -> InternalDatasetSchema:
    def convert_type(client_type: ClientDefinition) -> InternalDatasetSchemaTypeUnion:
        if isinstance(client_type, ClientDatasetScalarType):
            return InternalDatasetScalarType(
                id=client_type.id,
                dtype=client_type.dtype,
                tag_hints=client_type.tag_hints,
                nullable=client_type.nullable,
            )
        elif isinstance(client_type, ClientDatasetObjectType):
            return InternalDatasetObjectType(
                id=client_type.id,
                object={
                    k: convert_type(v.actual_instance)
                    for k, v in client_type.object.items()
                },
                tag_hints=client_type.tag_hints,
                nullable=client_type.nullable,
            )
        elif isinstance(client_type, ClientDatasetListType):
            return InternalDatasetListType(
                id=client_type.id,
                items=convert_type(client_type.items.actual_instance),
                tag_hints=client_type.tag_hints,
                nullable=client_type.nullable,
            )
        else:
            raise ValueError(f"Unknown type: {type(client_type)}")

    internal_columns = [
        InternalDatasetColumn(
            id=col.id,
            source_name=col.source_name,
            definition=convert_type(col.definition.actual_instance),
        )
        for col in schema.columns
    ]

    return InternalDatasetSchema(alias_mask=schema.alias_mask, columns=internal_columns)


def common_to_client_put_dataset_schema(
    internal_schema: InternalDatasetSchema,
) -> ClientPutDatasetSchema:
    def convert_type(
        internal_type: InternalDatasetSchemaTypeUnion,
    ) -> Union[DatasetScalarType, DatasetObjectType, DatasetListType]:
        if isinstance(internal_type, InternalDatasetScalarType):
            return DatasetScalarType(
                dtype=internal_type.dtype,
                tag_hints=internal_type.tag_hints,
                nullable=internal_type.nullable,
            )
        elif isinstance(internal_type, InternalDatasetObjectType):
            return DatasetObjectType(
                object={
                    k: ObjectValue(convert_type(v))
                    for k, v in internal_type.object.items()
                },
                tag_hints=internal_type.tag_hints,
                nullable=internal_type.nullable,
            )
        elif isinstance(internal_type, InternalDatasetListType):
            return DatasetListType(
                items=Items(convert_type(internal_type.items)),
                tag_hints=internal_type.tag_hints,
                nullable=internal_type.nullable,
            )
        else:
            raise ValueError(f"Unknown type: {type(internal_type)}")

    put_columns = [
        DatasetColumn(
            source_name=col.source_name,
            definition=Definition(convert_type(col.definition)),
        )
        for col in internal_schema.columns
    ]

    return ClientPutDatasetSchema(
        alias_mask=internal_schema.alias_mask,
        columns=put_columns,
    )
