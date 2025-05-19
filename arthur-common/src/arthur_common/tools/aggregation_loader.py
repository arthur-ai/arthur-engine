import inspect
import logging
from types import ModuleType
from typing import Type

import arthur_common.aggregations as agg_module
from arthur_common.aggregations.aggregator import (
    AggregationFunction,
    NumericAggregationFunction,
    SketchAggregationFunction,
)
from arthur_common.models.metrics import AggregationSpecSchema
from arthur_common.tools.aggregation_analyzer import FunctionAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AggregationLoader:
    @staticmethod
    def load_aggregations() -> (
        list[tuple[AggregationSpecSchema, Type[AggregationFunction]]]
    ):
        def find_subclasses(
            module: ModuleType,
            base_classes: tuple[type, ...],
            visited: set[ModuleType] = set(),
        ) -> set[type]:
            subclasses = set()
            visited.add(module)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, base_classes):
                    subclasses.add(obj)
                elif inspect.ismodule(obj) and obj not in visited:
                    subclasses.update(find_subclasses(obj, base_classes, visited))
            return subclasses

        base_classes = (SketchAggregationFunction, NumericAggregationFunction)
        agg_functions = find_subclasses(agg_module, base_classes)
        aggregation_specs = []
        """
          This seems to pick up duplicate functions somehow in different namespaces, ie:
           <class 'categorical_count.CategoricalCountAggregationFunction'>
           and
           <class 'arthur_common.aggregations.functions.categorical_count.CategoricalCountAggregationFunction'>
           so dedupe by id
        """
        aggregation_ids = set()
        for agg_function in agg_functions:
            try:
                func_spec = FunctionAnalyzer.analyze_aggregation_function(agg_function)
                logger.info(f"Found agg function {agg_function}")
                if func_spec.id in aggregation_ids:
                    continue
                aggregation_specs.append((func_spec, agg_function))
                aggregation_ids.add(func_spec.id)
            except Exception as e:
                logger.error(f"Failed to load aggregation function {agg_function}: {e}")
        return aggregation_specs
