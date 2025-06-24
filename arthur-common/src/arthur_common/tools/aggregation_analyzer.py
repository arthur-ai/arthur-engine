import inspect
import logging
import typing
import uuid
from typing import Any, Callable, get_type_hints

from arthur_common.aggregations import (
    AggregationFunction,
    NumericAggregationFunction,
    SketchAggregationFunction,
)
from arthur_common.models.metrics import (
    AggregationMetricType,
    AggregationSpecSchema,
    DatasetReference,
    MetricsColumnListParameterSchema,
    MetricsColumnParameterSchema,
    MetricsDatasetParameterSchema,
    MetricsLiteralParameterSchema,
    MetricsParameterSchemaUnion,
)
from arthur_common.models.schema_definitions import (
    DType,
    MetricColumnParameterAnnotation,
    MetricDatasetParameterAnnotation,
    MetricLiteralParameterAnnotation,
    MetricMultipleColumnParameterAnnotation,
    MetricsParameterAnnotationUnion,
)

logger = logging.getLogger(__name__)


class FunctionAnalyzer:
    @staticmethod
    def _python_type_to_scope_dtype(t: Any) -> DType:
        if t is int:
            return DType.INT
        elif t is str:
            return DType.STRING
        elif t is bool:
            return DType.BOOL
        elif t is float:
            return DType.FLOAT
        elif t is uuid.UUID:
            return DType.UUID
        elif t is DatasetReference:
            return DType.UUID
        elif typing.get_origin(t) is list:
            return DType.JSON
        elif typing.get_origin(t) is typing.Union:
            # handle union types to add support for Optional types only
            # extract the non-None type from Optional[T] = Union[T, None]
            args = typing.get_args(t)
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                return FunctionAnalyzer._python_type_to_scope_dtype(non_none_args[0])
            else:
                raise ValueError(
                    f"Union type {t} is not supported (only Optional[T] is supported).",
                )
        else:
            raise ValueError(f"Parameter type {t} is not supported.")

    @staticmethod
    def _get_metric_annotation_from_annotated(
        param_name: str,
        annotation: typing.Annotated,  # type: ignore
    ) -> MetricsParameterAnnotationUnion | None:
        arthur_metric_annotations = [
            m
            for m in annotation.__metadata__
            if isinstance(m, MetricsParameterAnnotationUnion)
        ]
        metric_annotation: MetricsParameterAnnotationUnion | None = None
        if len(arthur_metric_annotations) == 1:
            metric_annotation = arthur_metric_annotations[0]
        if len(arthur_metric_annotations) > 1:
            raise ValueError(
                f"Parameter {param_name} defines more than one metric annotation.",
            )
        return metric_annotation

    @staticmethod
    def _get_scope_metric_parameter_from_annotation(
        param_name: str,
        param_dtype: typing.Optional[DType],
        optional: bool,
        annotation: typing.Annotated,  # type: ignore
    ) -> MetricsParameterSchemaUnion:
        if annotation is None:
            return MetricsLiteralParameterSchema(
                parameter_key=param_name,
                optional=optional,
                parameter_dtype=param_dtype,
                friendly_name=param_name,
                description=f"A {param_dtype.value} value.",
            )
        elif isinstance(annotation, MetricLiteralParameterAnnotation):
            return MetricsLiteralParameterSchema(
                parameter_key=param_name,
                optional=optional,
                parameter_dtype=param_dtype,
                friendly_name=annotation.friendly_name,
                description=annotation.description,
            )
        elif isinstance(annotation, MetricDatasetParameterAnnotation):
            if param_dtype != DType.UUID:
                raise ValueError(
                    f"Dataset parameter {param_name} has type {param_dtype}, but should be a UUID.",
                )
            return MetricsDatasetParameterSchema(
                parameter_key=param_name,
                optional=optional,
                friendly_name=annotation.friendly_name,
                description=annotation.description,
                model_problem_type=annotation.model_problem_type,
            )
        elif isinstance(annotation, MetricMultipleColumnParameterAnnotation):
            if param_dtype != DType.JSON:
                raise ValueError(
                    f"Dataset parameter {param_name} has type {param_dtype}, but should be a JSON type (valid list expected).",
                )
            return MetricsColumnListParameterSchema(
                parameter_key=param_name,
                tag_hints=annotation.tag_hints,
                optional=optional,
                source_dataset_parameter_key=annotation.source_dataset_parameter_key,
                allowed_column_types=annotation.allowed_column_types,
                allow_any_column_type=annotation.allow_any_column_type,
                friendly_name=annotation.friendly_name,
                description=annotation.description,
            )
        elif isinstance(annotation, MetricColumnParameterAnnotation):
            if param_dtype != DType.STRING:
                raise ValueError(
                    f"Column parameter {param_name} has type {param_dtype}, but should be a string.",
                )
            return MetricsColumnParameterSchema(
                parameter_key=param_name,
                tag_hints=annotation.tag_hints,
                optional=optional,
                source_dataset_parameter_key=annotation.source_dataset_parameter_key,
                allowed_column_types=annotation.allowed_column_types,
                allow_any_column_type=annotation.allow_any_column_type,
                friendly_name=annotation.friendly_name,
                description=annotation.description,
            )
        else:
            raise ValueError(
                f"Parameter {param_name} has an unsupported annotation {annotation}.",
            )

    """
    Returns a list of parameter names, parameter types, scope-specific annotations.
    """

    @staticmethod
    def _extract_parameter_metadata(func: Callable) -> list[MetricsParameterSchemaUnion]:  # type: ignore
        parameter_schemas: list[MetricsParameterSchemaUnion] = []
        args = inspect.signature(func).parameters
        for name, param in args.items():
            if name == "self":
                continue
            if name == "ddb_conn":
                continue

            if param.annotation == inspect.Parameter.empty:
                raise ValueError(
                    f"{func.__name__} must provide type annotation for parameter {name}.",
                )
            parameter_schemas.append(
                FunctionAnalyzer._get_scope_metric_parameter_from_annotation(
                    name,
                    FunctionAnalyzer._python_type_to_scope_dtype(
                        get_type_hints(func)[name],
                    ),
                    param.default != inspect.Parameter.empty,
                    (
                        FunctionAnalyzer._get_metric_annotation_from_annotated(
                            name,
                            param.annotation,
                        )
                        if typing.get_origin(param.annotation) is typing.Annotated
                        else None
                    ),
                ),
            )

        return parameter_schemas

    @staticmethod
    def analyze_aggregation_function(agg_func: type) -> AggregationSpecSchema:
        # Check if X is a subclass of AggregationFunction
        if not issubclass(agg_func, AggregationFunction):
            raise TypeError(
                f"Class {agg_func.__name__} is not a subclass of AggregationFunction.",
            )

        if issubclass(agg_func, NumericAggregationFunction):
            metric_type = AggregationMetricType.NUMERIC
        elif issubclass(agg_func, SketchAggregationFunction):
            metric_type = AggregationMetricType.SKETCH
        else:
            raise ValueError(
                f"Class {agg_func.__name__} is not a subclass of SketchAggregationFunction, NumericAggregationFunction.",
            )
        # Check if X implements the required methods
        required_methods = ["aggregate", "id", "description", "display_name"]
        static_methods = ["description", "id", "display_name"]
        for method in required_methods:
            if not hasattr(agg_func, method) or not callable(getattr(agg_func, method)):
                raise AttributeError(
                    f"Class {agg_func.__name__} does not implement {method} method.",
                )

        for method in static_methods:
            if not is_static_method(getattr(agg_func, method)):
                raise AttributeError(f"Method {method} should be a staticmethod.")
        # Check if X passes the ABC implementation:
        try:
            agg_func()
        except TypeError as e:
            if "Can't instantiate abstract class" in str(e):
                logger.error(str(e))
                raise TypeError(
                    f"Class {agg_func.__name__} does not implement all the base class functions.",
                )
            else:
                # This is okay, it just means we didn't supply proper args to the __init__ function. The ABC mismatch would throw before this, so it must have passed
                pass

        aggregation_init_args: list[MetricsParameterSchemaUnion] = []

        # This is necessary because all the way down in the ABC class, some __init__ function is defined which we don't care about. Users should be able to exclude an init function and this allows them to do that.
        if has_custom_init(agg_func):
            aggregation_init_args = FunctionAnalyzer._extract_parameter_metadata(
                agg_func.__init__,
            )
        aggregate_args = FunctionAnalyzer._extract_parameter_metadata(
            agg_func.aggregate,
        )

        aggregation_id = agg_func.id()
        aggregation_description = agg_func.description()

        return AggregationSpecSchema(
            name=agg_func.display_name(),
            id=aggregation_id,
            # TODO: Require description, version
            description=aggregation_description,
            # version=0,
            metric_type=metric_type,
            init_args=aggregation_init_args,
            aggregate_args=aggregate_args,
        )


def has_custom_init(cls: type) -> bool:
    init_method = getattr(cls, "__init__", None)
    base_init_method = (
        getattr(cls.__base__, "__init__", None) if hasattr(cls, "__base__") else None
    )
    return init_method is not base_init_method


def is_static_method(method: type) -> bool:
    if inspect.isfunction(method):
        # Check if the method accepts no arguments or only default arguments
        argspec = inspect.getfullargspec(method)
        if len(argspec.args) == 0 and not argspec.varargs and not argspec.varkw:
            return True
    return False
