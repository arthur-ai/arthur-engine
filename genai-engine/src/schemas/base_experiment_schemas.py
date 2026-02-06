"""
Base experiment schemas shared across experiment types (prompt experiments, RAG experiments, etc.).

This module contains common schemas used by multiple experiment types, including:
- Experiment and test case status enums
- Variable mapping schemas
- Dataset reference schemas
- Evaluation reference and result schemas
- Common test case and execution schemas
"""

from enum import Enum
from typing import Annotated, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Discriminator, Field

from schemas.common_schemas import NewDatasetVersionRowColumnItemRequest


class ExperimentStatus(str, Enum):
    """Status of an experiment"""

    QUEUED = "queued"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class TestCaseStatus(str, Enum):
    """Status of a test case"""

    QUEUED = "queued"
    RUNNING = "running"
    EVALUATING = "evaluating"
    FAILED = "failed"
    COMPLETED = "completed"


# Variable mapping schemas
class DatasetColumnSource(BaseModel):
    """Reference to a dataset column"""

    name: str = Field(description="Name of the dataset column")


class ExperimentOutputSource(BaseModel):
    """Reference to experiment output"""

    json_path: Optional[str] = Field(
        default=None,
        description="Optional JSON path to extract from experiment output. Should use dot notation for array indexing (eg. response.objects.0.properties.category)",
    )


class JsonPathExperimentOutputSource(BaseModel):
    """Reference to experiment output using JSON path extraction (internal use)"""

    type: Literal["json_path"] = Field(
        default="json_path",
        description="Type of experiment output source",
    )
    json_path: Optional[str] = Field(
        default=None,
        description="JSON path to extract from experiment output. Should use dot notation for array indexing (eg. response.objects.0.properties.category)",
    )


class TransformVariableExperimentOutputSource(BaseModel):
    """Reference to experiment output using transform variable extraction (agentic experiments only)"""

    type: Literal["transform_variable"] = Field(
        default="transform_variable",
        description="Type of experiment output source",
    )
    transform_variable_name: str = Field(
        description="Name of the variable to extract from the transform. The transform_id comes from the eval configuration.",
    )


class DatasetColumnVariableSource(BaseModel):
    """Variable source from a dataset column"""

    type: Literal["dataset_column"] = Field(
        description="Type of source: 'dataset_column'",
    )
    dataset_column: DatasetColumnSource = Field(description="Dataset column source")


class ExperimentOutputVariableSource(BaseModel):
    """Variable source from experiment output"""

    type: Literal["experiment_output"] = Field(
        description="Type of source: 'experiment_output'",
    )
    experiment_output: ExperimentOutputSource = Field(
        description="Experiment output source",
    )


# Union type with discriminator (used for eval mappings)
VariableSource = Annotated[
    Union[DatasetColumnVariableSource, ExperimentOutputVariableSource],
    Discriminator("type"),
]


class EvalVariableMapping(BaseModel):
    """Mapping of an eval variable to its source (dataset column or experiment output)"""

    variable_name: str = Field(description="Name of the eval variable")
    source: VariableSource = Field(description="Source of the variable value")


# Reference schemas
class DatasetRefInput(BaseModel):
    """Reference to a dataset and version for input (without name)"""

    id: UUID = Field(description="Dataset ID")
    version: int = Field(description="Dataset version number")


class DatasetRef(DatasetRefInput):
    """Reference to a dataset and version (with name)"""

    name: str = Field(description="Dataset name")


class BaseEvalRef(BaseModel):
    """Base reference to an evaluation configuration"""

    name: str = Field(description="Name of the evaluation")
    version: int = Field(description="Version of the evaluation")


class EvalRef(BaseEvalRef):
    """Reference to an evaluation configuration"""

    variable_mapping: list[EvalVariableMapping] = Field(
        description="Mapping of eval variables to data sources",
    )


class EvalResultSummary(BaseModel):
    """Results for a single eval"""

    eval_name: str = Field(description="Name of the evaluation")
    eval_version: str = Field(description="Version of the evaluation")
    pass_count: int = Field(description="Number of test cases that passed")
    total_count: int = Field(description="Total number of test cases evaluated")


# Test case / result schemas
class InputVariable(BaseModel):
    """Input variable for a test case"""

    variable_name: str = Field(description="Name of the variable")
    value: str = Field(description="Value of the variable")


class EvalExecutionResult(BaseModel):
    """Results from an eval execution"""

    score: float = Field(description="Score from the evaluation")
    explanation: str = Field(description="Explanation of the score")
    cost: str = Field(description="Cost of the evaluation")


class EvalExecution(BaseModel):
    """Details of an eval execution"""

    eval_name: str = Field(description="Name of the evaluation")
    eval_version: str = Field(description="Version of the evaluation")
    eval_input_variables: list[InputVariable] = Field(
        description="Input variables used for the eval",
    )
    eval_results: Optional[EvalExecutionResult] = Field(
        default=None,
        description="Results from the eval (None if not yet executed)",
    )


class BaseExperimentSummary(BaseModel):
    """Generic summary of an experiment. Should be used as an inheritor class.
    See PromptExperimentSummary as an example.
    """

    id: str = Field(description="Unique identifier for the experiment")
    name: str = Field(description="Name of the experiment")
    description: Optional[str] = Field(
        default=None,
        description="Description of the experiment",
    )
    created_at: str = Field(description="ISO timestamp when experiment was created")
    finished_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when experiment finished",
    )
    status: ExperimentStatus = Field(description="Current status of the experiment")
    dataset_id: UUID = Field(description="ID of the dataset used")
    dataset_name: str = Field(description="Name of the dataset used")
    dataset_version: int = Field(description="Version of the dataset used")
    total_rows: int = Field(description="Total number of test rows in the experiment")
    completed_rows: int = Field(
        description="Number of test rows completed successfully",
    )
    failed_rows: int = Field(description="Number of test rows that failed")
    total_cost: Optional[str] = Field(
        default=None,
        description="Total cost of running the experiment",
    )


class BaseCreateExperimentRequest(BaseModel):
    """Base model for request to create a new experiment.
    See CreatePromptExperimentRequest for an example usage.
    """

    name: str = Field(description="Name for the experiment")
    description: Optional[str] = Field(
        default=None,
        description="Description of the experiment",
    )
    dataset_ref: DatasetRefInput = Field(description="Reference to the dataset to use")
    eval_list: list[EvalRef] = Field(description="List of evaluations to run")
    dataset_row_filter: Optional[List[NewDatasetVersionRowColumnItemRequest]] = Field(
        default=None,
        description="Optional list of column name and value filters. "
        "Only rows matching ALL specified column name-value pairs (AND condition) will be included in the experiment. "
        "If not specified, all rows from the dataset will be used.",
    )


class GroundBaseExperimentDetail(BaseModel):
    id: str = Field(description="Unique identifier for the experiment")
    name: str = Field(description="Name of the experiment")
    description: Optional[str] = Field(
        default=None,
        description="Description of the experiment",
    )
    created_at: str = Field(description="ISO timestamp when experiment was created")
    finished_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when experiment finished",
    )
    status: ExperimentStatus = Field(description="Current status of the experiment")
    total_rows: int = Field(description="Total number of test rows in the experiment")
    completed_rows: int = Field(
        description="Number of test rows completed successfully",
    )
    failed_rows: int = Field(description="Number of test rows that failed")
    total_cost: Optional[str] = Field(
        default=None,
        description="Total cost of running the experiment",
    )
    dataset_ref: DatasetRef = Field(description="Reference to the dataset used")
    dataset_row_filter: Optional[List[NewDatasetVersionRowColumnItemRequest]] = Field(
        default=None,
        description="Optional list of column name and value filters applied to dataset rows. "
        "Only rows matching ALL specified column name-value pairs (AND condition) were included in the experiment.",
    )
    notebook_id: Optional[str] = Field(
        default=None,
        description="Optional notebook ID this experiment is linked to",
    )


class BaseExperimentDetail(GroundBaseExperimentDetail):
    """Base model for experiment details.
    See PromptExperimentDetail for an example usage.
    """

    eval_list: list[EvalRef] = Field(description="List of evaluations being run")


class BaseTestCase(BaseModel):
    """Base model for experiment test cases.
    See RagTestCase for an example usage.
    """

    status: TestCaseStatus = Field(description="Status of the test case")
    dataset_row_id: str = Field(description="ID of the dataset row")
    total_cost: Optional[str] = Field(
        default=None,
        description="Total cost for this test case",
    )


class BaseConfigResult(BaseModel):
    """Base model for experiment results for a single config within a test case.
    See RagResult for an example usage.
    """

    status: TestCaseStatus = Field(description="Status of the test case")
    dataset_row_id: str = Field(description="ID of the dataset row")
    evals: list[EvalExecution] = Field(
        description="Evaluation results for this specific config",
    )
    total_cost: Optional[str] = Field(
        default=None,
        description="Total cost for this config test case execution",
    )


class BaseResult(BaseModel):
    """Base model for the results from an experiment execution with evals.
    See PromptResult for an example usage.
    """

    evals: list[EvalExecution] = Field(
        description="Evaluation results for this execution",
    )
