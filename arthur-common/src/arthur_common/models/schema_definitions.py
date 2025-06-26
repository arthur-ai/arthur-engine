from __future__ import annotations

from enum import Enum
from typing import Optional, Self, Union
from uuid import UUID, uuid4

from arthur_common.models.datasets import ModelProblemType
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class ScopeSchemaTag(str, Enum):
    LLM_CONTEXT = "llm_context"
    LLM_PROMPT = "llm_prompt"
    LLM_RESPONSE = "llm_response"
    PRIMARY_TIMESTAMP = "primary_timestamp"
    CATEGORICAL = "categorical"
    CONTINUOUS = "continuous"
    PREDICTION = "prediction"
    GROUND_TRUTH = "ground_truth"
    PIN_IN_DEEP_DIVE = "pin_in_deep_dive"


class DType(str, Enum):
    UNDEFINED = "undefined"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "str"
    UUID = "uuid"
    TIMESTAMP = "timestamp"
    DATE = "date"
    JSON = "json"
    IMAGE = "image"


class MetricParameterAnnotation(BaseModel):
    optional: bool = Field(
        False,
        description="Boolean denoting if the parameter is optional.",
    )
    friendly_name: str = Field(
        description="User facing name of the parameter.",
    )
    description: str = Field(
        description="Description of the parameter.",
    )


class MetricDatasetParameterAnnotation(MetricParameterAnnotation):
    model_problem_type: Optional[ModelProblemType] = Field(
        default=None,
        description="Model problem type that is applicable to this parameter.",
    )


class MetricLiteralParameterAnnotation(MetricParameterAnnotation):
    parameter_dtype: DType = Field(description="Data type of the parameter.")


class MetricColumnParameterAnnotation(MetricParameterAnnotation):
    tag_hints: list[ScopeSchemaTag] = Field(
        [],
        description="List of tags that are applicable to this parameter. Datasets with columns that have matching tags can be inferred this way.",
    )
    source_dataset_parameter_key: str = Field(
        description="Name of the parameter that provides the dataset to be used for this column.",
    )
    allowed_column_types: Optional[list[SchemaTypeUnion]] = Field(
        default=None,
        description="List of column types applicable to this parameter",
    )
    allow_any_column_type: bool = Field(
        False,
        description="Indicates if this metric parameter can accept any column type.",
    )

    @model_validator(mode="after")
    def column_type_combination_validator(self) -> Self:
        if self.allowed_column_types and self.allow_any_column_type:
            raise ValueError(
                "Parameter cannot allow any column while also explicitly listing applicable ones.",
            )
        return self


class MetricMultipleColumnParameterAnnotation(MetricColumnParameterAnnotation):
    pass


MetricsParameterAnnotationUnion = (
    MetricDatasetParameterAnnotation
    | MetricLiteralParameterAnnotation
    | MetricColumnParameterAnnotation
    | MetricMultipleColumnParameterAnnotation
)


class Type(BaseModel):
    # There's bound to be something in common here eventually
    pass


class ScalarType(Type):
    dtype: DType

    def __hash__(self) -> int:
        return hash(self.dtype)


class ObjectType(Type):
    object: dict[str, SchemaTypeUnion]

    def __getitem__(self, key: str) -> SchemaTypeUnion:
        return self.object[key]

    def __hash__(self) -> int:
        # Combine the hash of all dictionary values
        combined_hash = 0
        for name, col in self.object.items():
            combined_hash ^= hash(name)
            combined_hash ^= hash(col)
        return combined_hash


class ListType(Type):
    items: SchemaTypeUnion

    def __hash__(self) -> int:
        return hash(self.items)


class DatasetSchemaType(Type):
    tag_hints: list[ScopeSchemaTag] = []
    nullable: Optional[bool] = True
    id: UUID = Field(default_factory=uuid4, description="Unique ID of the schema node.")


class DatasetScalarType(ScalarType, DatasetSchemaType):
    def __hash__(self) -> int:
        return hash(self.dtype)

    def to_base_type(self) -> ScalarType:
        return ScalarType(dtype=self.dtype)


class DatasetObjectType(DatasetSchemaType):
    object: dict[str, DatasetSchemaTypeUnion]

    def __getitem__(self, key: str) -> DatasetSchemaTypeUnion:
        return self.object[key]

    def __hash__(self) -> int:
        # Combine the hash of all dictionary values
        combined_hash = 0
        for name, col in self.object.items():
            combined_hash ^= hash(name)
            combined_hash ^= hash(col)
        return combined_hash

    def to_base_type(self) -> ObjectType:
        return ObjectType(object={k: v.to_base_type() for k, v in self.object.items()})


class DatasetListType(DatasetSchemaType):
    items: DatasetSchemaTypeUnion

    def __hash__(self) -> int:
        return hash(self.items)

    def to_base_type(self) -> ListType:
        return ListType(items=self.items.to_base_type())


class DatasetColumn(BaseModel):
    id: UUID = Field(default_factory=uuid4, description="Unique ID of the column.")
    source_name: str
    definition: DatasetSchemaTypeUnion

    def __hash__(self) -> int:
        combined_hash = 0
        combined_hash ^= hash(self.source_name)
        combined_hash ^= hash(self.definition)
        return combined_hash


class PutDatasetSchema(BaseModel):
    alias_mask: dict[UUID, str]
    columns: list[DatasetColumn]

    def regenerate_ids(self) -> PutDatasetSchema:
        new_columns = []
        new_alias_mask = {}
        for column in self.columns:
            new_id = uuid4()
            new_columns.append(
                DatasetColumn(
                    id=new_id,
                    source_name=column.source_name,
                    definition=self._regenerate_definition_ids(column.definition),
                ),
            )
            if column.id in self.alias_mask:
                new_alias_mask[new_id] = self.alias_mask[column.id]

        self.columns = new_columns
        self.alias_mask = new_alias_mask
        return self

    @staticmethod
    def _regenerate_definition_ids(
        definition: DatasetSchemaTypeUnion,
    ) -> DatasetSchemaTypeUnion:
        new_def = definition.model_copy(deep=True)
        new_def.id = uuid4()

        if isinstance(new_def, DatasetObjectType):
            new_def.object = {
                k: PutDatasetSchema._regenerate_definition_ids(v)
                for k, v in new_def.object.items()
            }
        elif isinstance(new_def, DatasetListType):
            new_def.items = PutDatasetSchema._regenerate_definition_ids(new_def.items)

        return new_def


# This needs to be a separate model than PutDatasetSchema because of this generated field not being consumed correctly by the client generator
# Issue tracked externally here: https://github.com/OpenAPITools/openapi-generator/issues/4190
class DatasetSchema(PutDatasetSchema):
    @computed_field  # type: ignore[prop-decorator]
    @property
    def column_names(self) -> dict[UUID, str]:
        col_names = {column.id: column.source_name for column in self.columns}
        col_names.update(self.alias_mask)
        return col_names

    model_config = ConfigDict(
        json_schema_mode_override="serialization",
    )


SchemaTypeUnion = Union[ScalarType, ObjectType, ListType]
DatasetSchemaTypeUnion = Union[DatasetScalarType, DatasetObjectType, DatasetListType]

from uuid import uuid4


def create_dataset_scalar_type(dtype: DType) -> DatasetScalarType:
    return DatasetScalarType(id=uuid4(), dtype=dtype)


def create_dataset_object_type(
    object_dict: dict[str, DatasetSchemaTypeUnion],
) -> DatasetObjectType:
    return DatasetObjectType(id=uuid4(), object={k: v for k, v in object_dict.items()})


def create_dataset_list_type(items: DatasetSchemaTypeUnion) -> DatasetListType:
    return DatasetListType(id=uuid4(), items=items)


def create_shield_rule_results_schema() -> DatasetListType:
    return create_dataset_list_type(
        create_dataset_object_type(
            {
                "id": create_dataset_scalar_type(DType.UUID),
                "name": create_dataset_scalar_type(DType.STRING),
                "rule_type": create_dataset_scalar_type(DType.STRING),
                "scope": create_dataset_scalar_type(DType.STRING),
                "result": create_dataset_scalar_type(DType.STRING),
                "latency_ms": create_dataset_scalar_type(DType.INT),
                "details": create_dataset_object_type(
                    {
                        "message": create_dataset_scalar_type(DType.STRING),
                        "claims": create_dataset_list_type(
                            create_dataset_object_type(
                                {
                                    "claim": create_dataset_scalar_type(DType.STRING),
                                    "valid": create_dataset_scalar_type(DType.BOOL),
                                    "reason": create_dataset_scalar_type(DType.STRING),
                                },
                            ),
                        ),
                        "pii_entities": create_dataset_list_type(
                            create_dataset_object_type(
                                {
                                    "entity": create_dataset_scalar_type(DType.STRING),
                                    "span": create_dataset_scalar_type(DType.STRING),
                                    "confidence": create_dataset_scalar_type(
                                        DType.FLOAT,
                                    ),
                                },
                            ),
                        ),
                        "toxicity_score": create_dataset_scalar_type(DType.FLOAT),
                        "regex_matches": create_dataset_list_type(
                            create_dataset_object_type(
                                {
                                    "matching_text": create_dataset_scalar_type(
                                        DType.STRING,
                                    ),
                                    "pattern": create_dataset_scalar_type(DType.STRING),
                                },
                            ),
                        ),
                        "keyword_matches": create_dataset_list_type(
                            create_dataset_object_type(
                                {
                                    "keyword": create_dataset_scalar_type(DType.STRING),
                                },
                            ),
                        ),
                    },
                ),
            },
        ),
    )


def create_shield_prompt_schema() -> DatasetObjectType:
    return create_dataset_object_type(
        {
            "id": create_dataset_scalar_type(DType.UUID),
            "inference_id": create_dataset_scalar_type(DType.UUID),
            "result": create_dataset_scalar_type(DType.STRING),
            "created_at": create_dataset_scalar_type(DType.INT),
            "updated_at": create_dataset_scalar_type(DType.INT),
            "message": create_dataset_scalar_type(DType.STRING),
            "prompt_rule_results": create_shield_rule_results_schema(),
            "tokens": create_dataset_scalar_type(DType.INT),
        },
    )


def create_shield_response_schema() -> DatasetObjectType:
    return create_dataset_object_type(
        {
            "id": create_dataset_scalar_type(DType.UUID),
            "inference_id": create_dataset_scalar_type(DType.UUID),
            "result": create_dataset_scalar_type(DType.STRING),
            "created_at": create_dataset_scalar_type(DType.INT),
            "updated_at": create_dataset_scalar_type(DType.INT),
            "message": create_dataset_scalar_type(DType.STRING),
            "context": create_dataset_scalar_type(DType.STRING),
            "response_rule_results": create_shield_rule_results_schema(),
            "tokens": create_dataset_scalar_type(DType.INT),
        },
    )


def create_shield_inference_feedback_schema() -> DatasetListType:
    return create_dataset_list_type(
        create_dataset_object_type(
            {
                "id": create_dataset_scalar_type(DType.UUID),
                "inference_id": create_dataset_scalar_type(DType.UUID),
                "target": create_dataset_scalar_type(DType.STRING),
                "score": create_dataset_scalar_type(DType.FLOAT),
                "reason": create_dataset_scalar_type(DType.STRING),
                "user_id": create_dataset_scalar_type(DType.UUID),
                "created_at": create_dataset_scalar_type(DType.TIMESTAMP),
                "updated_at": create_dataset_scalar_type(DType.TIMESTAMP),
            },
        ),
    )


def SHIELD_SCHEMA() -> DatasetSchema:
    return DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name="id",
                definition=create_dataset_scalar_type(DType.UUID),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="result",
                definition=create_dataset_scalar_type(DType.STRING),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="created_at",
                definition=create_dataset_scalar_type(DType.INT),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="updated_at",
                definition=create_dataset_scalar_type(DType.INT),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="task_id",
                definition=create_dataset_scalar_type(DType.UUID),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="conversation_id",
                definition=create_dataset_scalar_type(DType.STRING),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="inference_prompt",
                definition=create_shield_prompt_schema(),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="inference_response",
                definition=create_shield_response_schema(),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="inference_feedback",
                definition=create_shield_inference_feedback_schema(),
            ),
        ],
    )


SHIELD_RESPONSE_SCHEMA = create_shield_response_schema().to_base_type()
SHIELD_PROMPT_SCHEMA = create_shield_prompt_schema().to_base_type()
