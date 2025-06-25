from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID

from arthur_common.models.datasets import ModelProblemType
from arthur_common.models.schema_definitions import (
    DType,
    SchemaTypeUnion,
    ScopeSchemaTag,
)
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


# Temporary limited list, expand this as we grow and make it more in line with custom transformations later on
class AggregationType(str, Enum):
    MIN = "min"
    MAX = "max"
    AVERAGE = "average"
    COUNT = "count"
    # Highly specific for Shield MVP work, to be abtracted more along the lines of the above later
    SHIELD_INFERENCE_PASS_FAIL_COUNT = "shield_inference_pass_fail_count"
    SHIELD_PROMPT_RESPONSE_PASS_FAIL_COUNT = "shield_prompt_response_pass_fail_count"
    SHIELD_INFERENCE_RULE_COUNT = "shield_inference_rule_count"
    SHIELD_INFERENCE_RULE_PASS_FAIL_COUNT = "shield_inference_rule_pass_fail_count"
    SHIELD_INFERENCE_RULE_TOXICITY_SCORE = "shield_inference_rule_toxicity_score"
    SHIELD_INFERENCE_RULE_PII_SCORE = "shield_inference_rule_pii_score"
    SHIELD_INFERENCE_HALLUCINATION_COUNT = "shield_inference_hallucination_count"
    SHIELD_INFERENCE_RULE_CLAIM_COUNT = "shield_inference_rule_claim_count"
    SHIELD_INFERENCE_RULE_CLAIM_PASS_COUNT = "shield_inference_rule_claim_pass_count"
    SHIELD_INFERENCE_RULE_CLAIM_FAIL_COUNT = "shield_inference_rule_claim_fail_count"
    SHIELD_INFERENCE_RULE_LATENCY = "shield_inference_rule_latency"


class Dimension(BaseModel):
    name: str = Field(description="Name of the dimension.")
    value: str = Field(description="Value of the dimension.")


class NumericPoint(BaseModel):
    timestamp: datetime = Field(
        description="Timestamp with timezone. Should be the timestamp of the start of the interval covered by 'value'.",
    )
    value: float = Field(description="Floating point value for the metric.")


class NumericTimeSeries(BaseModel):
    dimensions: list[Dimension] = Field(
        description="List of dimensions for the series. If multiple dimensions are uploaded with the same key, "
        "the one that is kept is undefined.",
    )
    values: list[NumericPoint] = Field(
        description="List of numeric time series points.",
    )


class SketchPoint(BaseModel):
    timestamp: datetime = Field(
        description="Timestamp with timezone. Should be the timestamp of the start of the interval covered by 'value'.",
    )
    value: str = Field(description="Base64-encoded string representation of a sketch.")


class SketchTimeSeries(BaseModel):
    dimensions: list[Dimension] = Field(
        description="List of dimensions for the series. If multiple dimensions are uploaded with the same key, "
        "the one that is kept is undefined.",
    )
    values: list[SketchPoint] = Field(
        description="List of sketch-based time series points.",
    )


class BaseMetric(BaseModel):
    name: str = Field(description="Name of the metric.")


class NumericMetric(BaseMetric):
    numeric_series: list[NumericTimeSeries] = Field(
        description="List of numeric time series to upload for the metric.",
    )


class SketchMetric(BaseMetric):
    sketch_series: list[SketchTimeSeries] = Field(
        description="List of sketch-based time series to upload for the metric.",
    )


class SystemMetricEventKind(Enum):
    MODEL_JOB_FAILURE = "model_job_failure"


class SystemMetric(BaseModel):
    event_kind: SystemMetricEventKind = Field(
        description="Kind of the system metric event.",
    )
    timestamp: datetime = Field(
        description="Timezone-aware timestamp of the system metric event.",
    )
    dimensions: list[Dimension] = Field(
        description="List of dimensions for the systems metric. If multiple dimensions are uploaded with the same key, "
        "the one that is kept is undefined.",
    )


class AggregationMetricType(Enum):
    SKETCH = "sketch"
    NUMERIC = "numeric"


class MetricsParameterSchema(BaseModel):
    parameter_key: str = Field(description="Name of the parameter.")
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


class MetricsDatasetParameterSchema(MetricsParameterSchema):
    parameter_type: Literal["dataset"] = "dataset"
    model_problem_type: Optional[ModelProblemType] = Field(
        default=None,
        description="Model problem type of the parameter. If not set, any model problem type is allowed.",
    )


class MetricsLiteralParameterSchema(MetricsParameterSchema):
    parameter_type: Literal["literal"] = "literal"
    parameter_dtype: DType = Field(description="Data type of the parameter.")


class MetricsColumnParameterSchema(MetricsParameterSchema):
    parameter_type: Literal["column"] = "column"
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


# Not used /implemented yet. Might turn into group by column list
class MetricsColumnListParameterSchema(MetricsColumnParameterSchema):
    parameter_type: Literal["column_list"] = "column_list"


MetricsParameterSchemaUnion = (
    MetricsDatasetParameterSchema
    | MetricsLiteralParameterSchema
    | MetricsColumnParameterSchema
    | MetricsColumnListParameterSchema
)


@dataclass
class DatasetReference:
    dataset_name: str
    dataset_table_name: str
    dataset_id: UUID


class AggregationSpecSchema(BaseModel):
    name: str = Field(description="Name of the aggregation function.")
    id: UUID = Field(description="Unique identifier of the aggregation function.")
    description: str = Field(
        description="Description of the aggregation function and what it aggregates.",
    )
    # version: int = Field("Version number of the aggregation function.")
    metric_type: AggregationMetricType = Field(
        description="Return type of the aggregations aggregate function.",
    )  # Sketch, Numeric
    init_args: list[MetricsParameterSchemaUnion] = Field(
        description="List of parameters to the aggregation's init function.",
    )
    aggregate_args: list[MetricsParameterSchemaUnion] = Field(
        description="List of parameters to the aggregation's aggregate function.",
    )

    @model_validator(mode="after")
    def column_dataset_references_exist(self) -> Self:
        dataset_parameter_keys = [
            p.parameter_key
            for p in self.aggregate_args
            if isinstance(p, MetricsDatasetParameterSchema)
        ]
        for param in self.aggregate_args:
            if (
                isinstance(
                    param,
                    (MetricsColumnParameterSchema, MetricsColumnListParameterSchema),
                )
                and param.source_dataset_parameter_key not in dataset_parameter_keys
            ):
                raise ValueError(
                    f"Column parameter '{param.parameter_key}' references dataset parameter '{param.source_dataset_parameter_key}' which does not exist.",
                )
        return self
