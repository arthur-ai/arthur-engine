from enum import Enum


class ModelProblemType(str, Enum):
    REGRESSION = "regression"
    BINARY_CLASSIFICATION = "binary_classification"
    ARTHUR_SHIELD = "arthur_shield"
    CUSTOM = "custom"
    MULTICLASS_CLASSIFICATION = "multiclass_classification"


class DatasetFileType(str, Enum):
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"


class DatasetJoinKind(str, Enum):
    INNER = "inner"
    LEFT_OUTER = "left_outer"
    OUTER = "outer"
    RIGHT_OUTER = "right_outer"
