"""
Services package for SpanRepository refactoring.

This package contains the separated services that handle the distinct responsibilities
previously managed by the monolithic SpanRepository class:

- TraceIngestionService: Protobuf processing and data validation
- SpanQueryService: Database queries and pagination
- MetricsIntegrationService: Metrics computation and storage
- TreeBuildingService: Span tree construction
"""

from .metrics_integration_service import MetricsIntegrationService
from .span_query_service import SpanQueryService
from .trace_ingestion_service import TraceIngestionService
from .tree_building_service import TreeBuildingService

__all__ = [
    "TraceIngestionService",
    "SpanQueryService",
    "MetricsIntegrationService",
    "TreeBuildingService",
]
