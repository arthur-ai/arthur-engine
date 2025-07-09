import json
import logging
import uuid
from datetime import datetime
from typing import List

from db_models.db_models import DatabaseSpan, DatabaseMetricResult
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError
from opentelemetry import trace
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from repositories.tasks_metrics_repository import TasksMetricsRepository
from repositories.metrics_repository import MetricRepository
from dependencies import get_metrics_engine
from schemas.enums import PaginationSortMethod
from schemas.internal_schemas import Span, MetricResult
from schemas.metric_schemas import MetricRequest    
from sqlalchemy import and_, asc, desc, insert, select
from sqlalchemy.orm import Session
from utils import trace as trace_utils
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class SpanRepository:
    def __init__(self, db_session: Session, tasks_metrics_repo: TasksMetricsRepository, metrics_repo: MetricRepository):
        self.db_session = db_session
        self.tasks_metrics_repo = tasks_metrics_repo
        self.metrics_repo = metrics_repo

    @tracer.start_as_current_span("store_traces")
    def create_traces(self, trace_data: bytes):
        """
        Process trace data from protobuf format and store in database using bulk insert.
        Optimized with single transaction for all operations.

        Args:
            trace_data: Raw protobuf trace data

        Returns:
        tuple: (total_spans, accepted_spans, unnecessary_spans, rejected_spans, rejected_reasons)
        """
        total_spans = 0
        accepted_spans = 0
        rejected_spans = 0
        rejected_reasons = []

        try:
            # Parse the protobuf message
            json_traces = self._grpc_trace_to_dict(trace_data)

            # Process each span and prepare data for bulk insert
            spans_data = []
            for resource_span in json_traces.get("resourceSpans", []):
                for scope_span in resource_span.get("scopeSpans", []):
                    for span_data in scope_span.get("spans", []):
                        total_spans += 1
                        span_dict = self._clean_span_data(span_data)
                        # span_dict will be None only if span data is invalid
                        if span_dict:
                            span_dict["id"] = str(uuid.uuid4())
                            spans_data.append(span_dict)
                            accepted_spans += 1
                        else:
                            rejected_spans += 1
                            rejected_reasons.append("Invalid span data")

            if spans_data:
                # Store all spans
                try:
                    logger.debug(f"Processing {len(spans_data)} spans")
                    self.store_spans(spans_data, commit=True)
                    logger.debug("Spans stored successfully")
                except Exception as e:
                    logger.error(f"Error storing spans: {e}")
                    raise e

            return (
                total_spans,
                accepted_spans,
                rejected_spans,
                rejected_reasons,
            )

        except DecodeError as e:
            raise DecodeError("Failed to parse protobuf message.") from e

    def query_spans(
        self,
        sort: PaginationSortMethod,
        page: int,
        page_size: int = 10,
        trace_ids: list[str] = None,
        span_ids: list[str] = None,
        task_ids: list[str] = None,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> list[Span]:
        """
        Query spans with efficient filtering and pagination.
        Only loads necessary fields and applies filters at the database level.
        """
        # Build the query
        query = self._build_spans_query(
            trace_ids=trace_ids,
            span_ids=span_ids,
            task_ids=task_ids,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
            page=page,
            page_size=page_size,
        )

        # Execute query and transform results
        # Use unique() to handle joined eager loads against collections
        results = self.db_session.execute(query).scalars().unique().all()
        return [Span._from_database_model(span) for span in results]

    def store_spans(self, spans: list[dict], commit: bool = True):
        """
        Store spans in the database with optional commit control.
        """
        if not spans:
            return
            
        stmt = insert(DatabaseSpan).values(spans)
        self.db_session.execute(stmt)
        
        if commit:
            self.db_session.commit()
            
        logger.debug(f"Stored {len(spans)} spans (commit={commit})")

    def _build_spans_query(
        self,
        page: int,
        trace_ids: list[str] = None,
        span_ids: list[str] = None,
        task_ids: list[str] = None,
        start_time: datetime = None,
        end_time: datetime = None,
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        page_size: int = 10,
    ) -> select:
        """
        Build a query for spans with the given filters.
        This method only constructs the query without executing it.
        """
        query = select(DatabaseSpan)

        # Build filter conditions
        conditions = []
        if task_ids:
            conditions.append(DatabaseSpan.task_id.in_(task_ids))
        if trace_ids:
            conditions.append(DatabaseSpan.trace_id.in_(trace_ids))
        if span_ids:
            conditions.append(DatabaseSpan.span_id.in_(span_ids))
        if start_time:
            conditions.append(DatabaseSpan.created_at >= start_time)
        if end_time:
            conditions.append(DatabaseSpan.created_at <= end_time)

        # Apply filters if any conditions exist
        if conditions:
            query = query.where(and_(*conditions))

        # Apply sorting
        if sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseSpan.created_at))
        elif sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseSpan.created_at))

        # Apply pagination
        if page is not None and page_size is not None:
            query = query.offset(page * page_size).limit(page_size)

        return query

    def _grpc_trace_to_dict(self, trace_data: bytes) -> dict:
        try:
            trace_request = ExportTraceServiceRequest()
            trace_request.ParseFromString(trace_data)
            json_traces = MessageToDict(trace_request)
            return json_traces
        except DecodeError as e:
            raise DecodeError("Failed to decode protobuf message.") from e

    def _get_span_kind(self, span_data: dict) -> str:
        """Extract span kind from span data"""
        if "attributes" not in span_data:
            return None

        for attr in span_data.get("attributes", []):
            key = attr.get("key")
            value = attr.get("value", {})
            if key == "openinference.span.kind":
                return value.get("stringValue")
        return None

    def _get_parent_span_id(self, span_data: dict) -> str:
        """Extract parent span ID from span data"""
        if "parentSpanId" in span_data:
            return trace_utils.convert_id_to_hex(span_data.get("parentSpanId"))
        return None

    def _get_task_id_from_parent(self, parent_span_id: str) -> str:
        """
        Get the task ID from a parent span if it exists in the database
        """
        if not parent_span_id:
            return None
            
        try:
            parent_span = (
                self.db_session.query(DatabaseSpan)
                .filter(DatabaseSpan.span_id == parent_span_id)
                .first()
            )
            return parent_span.task_id if parent_span else None
        except Exception as e:
            logger.warning(f"Error retrieving parent span {parent_span_id}: {e}")
            return None

    def _extract_timestamps(self, span_data: dict) -> tuple[datetime, datetime]:
        """Extract and convert timestamps from span data"""
        start_time = None
        end_time = None

        if "startTimeUnixNano" in span_data:
            start_time_ns = int(span_data.get("startTimeUnixNano", 0))
            start_time = trace_utils.timestamp_ns_to_datetime(start_time_ns)

        if "endTimeUnixNano" in span_data:
            end_time_ns = int(span_data.get("endTimeUnixNano", 0))
            end_time = trace_utils.timestamp_ns_to_datetime(end_time_ns)
        return start_time, end_time

    def _get_task_id(self, metadata: dict) -> str:
        """
        Get the task ID from the metadata
        Return None if the task ID is not present
        """
        return metadata.get("arthur.task", None)

    def _get_metadata(self, span_data: dict) -> dict:
        """
        Get the metadata from the span data
        """
        attrs = span_data.get("attributes", [])
        for attr in attrs:
            if attr.get("key") == "metadata":
                return json.loads(attr.get("value").get("stringValue"))
        return {}

    def _clean_span_data(self, span_data: dict) -> dict:
        """
        Clean and process span data, returning None if the span data is invalid.
        Now accepts spans without task IDs if they have parent spans.
        """
        # Extract basic span data
        span_dict = {
            "trace_id": trace_utils.convert_id_to_hex(span_data.get("traceId")),
            "span_id": trace_utils.convert_id_to_hex(span_data.get("spanId")),
        }

        # Extract parent span ID
        parent_span_id = self._get_parent_span_id(span_data)
        if parent_span_id:
            span_dict["parent_span_id"] = parent_span_id

        # Extract span kind
        span_kind = self._get_span_kind(span_data)
        if span_kind:
            span_dict["span_kind"] = span_kind

        # Extract timestamps
        start_time, end_time = self._extract_timestamps(span_data)
        span_dict["start_time"] = start_time
        span_dict["end_time"] = end_time

        # Extract attributes and metadata
        metadata = self._get_metadata(span_data)
        task_id = self._get_task_id(metadata)
        
        # If no task ID in current span, try to get it from parent span
        if not task_id and parent_span_id:
            task_id = self._get_task_id_from_parent(parent_span_id)
            if task_id:
                logger.debug(f"Using task ID from parent span {parent_span_id}: {task_id}")
        
        # Store the span even if it doesn't have a task ID (it might be a child span)
        span_dict["task_id"] = task_id
        span_dict["raw_data"] = span_data
        
        # Log warning for spans without task ID but don't skip them
        if not task_id:
            logger.warning(f"No task ID found for span {span_dict['span_id']} (parent: {parent_span_id}). Storing anyway.")
            
        return span_dict

    def query_spans_with_metrics(
        self,
        task_ids: list[str],
        sort: PaginationSortMethod,
        page: int,
        page_size: int = 10,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> list[Span]:
        """
        Query spans with metrics for the given task IDs.
        Computes metrics for spans that don't have them and returns spans with embedded metrics.
        """
        if not task_ids:
            raise ValueError("At least one task_id is required")
            
        # Get spans for the specified tasks
        spans = self.query_spans(
            task_ids=task_ids,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        
        if not spans:
            return []
            
        # Get existing metric results for these spans
        span_ids = [span.id for span in spans]
        existing_metric_results = self._get_metric_results_for_spans(span_ids)
        
        # Identify spans that need metrics computed
        spans_without_metrics = []
        for span in spans:
            if span.id not in existing_metric_results:
                spans_without_metrics.append(span)
        
        # Compute metrics for spans that don't have them
        if spans_without_metrics:
            logger.debug(f"Computing metrics for {len(spans_without_metrics)} spans")
            new_metric_results = self._compute_metrics_for_spans(spans_without_metrics)
            self._store_metric_results(new_metric_results)
            # Update existing results with newly computed ones
            existing_metric_results.update(new_metric_results)
        
        # Embed metrics into spans
        for span in spans:
            span.metric_results = existing_metric_results.get(span.id, [])
            
        return spans
    
    def _get_metric_results_for_spans(self, span_ids: list[str]) -> dict[str, list[MetricResult]]:
        """
        Get existing metric results for the given span IDs.
        Returns a dict mapping span_id to list of MetricResult objects.
        """
        if not span_ids:
            return {}
        
        metric_results = (
            self.db_session.query(DatabaseMetricResult)
            .filter(DatabaseMetricResult.span_id.in_(span_ids))
            .all()
        )
        
        # Group by span_id
        results_by_span = {}
        for db_result in metric_results:
            span_id = db_result.span_id
            if span_id not in results_by_span:
                results_by_span[span_id] = []
            results_by_span[span_id].append(MetricResult._from_database_model(db_result))
            
        return results_by_span

    def _compute_metrics_for_spans(self, spans: list[Span]) -> dict[str, list[MetricResult]]:
        """
        Compute metrics for the given spans.
        Returns a dict mapping span_id to list of MetricResult objects.
        """
        if not spans:
            return {}
            
        metrics_engine = get_metrics_engine()
        metrics_results = {}
        
        logger.debug(f"Computing metrics for {len(spans)} spans")
        
        for span in spans:
            task_id = span.task_id
            if not task_id:
                logger.warning(f"Span {span.id} has no task_id, skipping metric computation")
                continue
            
            # Only compute metrics for LLM spans
            span_kind = span.span_kind
            if span_kind != "LLM":
                logger.debug(f"Skipping metric computation for span {span.id} - span kind is {span_kind}, not LLM")
                continue
                
            try:
                # Convert span to MetricRequest format
                span_request = self._span_to_metric_request(span)
                
                # Get metrics for this task
                metric_ids = self.tasks_metrics_repo.get_task_metrics_ids_cached(task_id)
                metrics = self.metrics_repo.get_metrics_by_metric_id(metric_ids)
                
                if not metrics:
                    logger.debug(f"No metrics found for task {task_id}")
                    continue
                
                # Compute metrics
                results = metrics_engine.evaluate(span_request, metrics)
                
                # Set span_id and metric_id on results
                metrics_results[span.id] = []
                for i, result in enumerate(results):
                    if i < len(metrics):
                        metric_id = metrics[i].id
                        result.span_id = span.id
                        result.metric_id = metric_id
                        metrics_results[span.id].append(result)
                
                logger.debug(f"Computed {len(results)} metrics for span {span.id}")
                
            except Exception as e:
                logger.error(f"Error computing metrics for span {span.id}: {e}")
                # Continue processing other spans even if one fails
                continue
        
        logger.debug(f"Total metrics computed: {sum(len(results) for results in metrics_results.values())}")
        return metrics_results

    def _span_to_metric_request(self, span: Span) -> MetricRequest:
        """
        Convert a Span to MetricRequest format for metric computation.
        """
        span_features = trace_utils.extract_span_features(span.raw_data)

        context = span_features["context"]

        if "content" in span_features["response"]:
            response = span_features["response"]["content"]
        elif "tool_calls" in span_features["response"]:
            # Handle case where response is a tool call
            response = json.dumps(span_features["response"]["tool_calls"])
        else:
            response = json.dumps(span_features["response"])
        
        return MetricRequest(
            system_prompt=span_features["system_prompt"],
            user_query=span_features["user_query"],
            context=context,
            response=response,
        )

    def _store_metric_results(self, metrics_results: dict[str, list[MetricResult]]):
        """
        Store metric results in the database.
        """
        if not metrics_results:
            return
            
        # Collect all metric results to store
        metric_results_to_insert = []
        
        for span_id, results in metrics_results.items():
            for result in results:
                # Prepare metric result for bulk insert
                metric_results_to_insert.append({
                    'id': result.id,
                    'created_at': result.created_at,
                    'updated_at': result.updated_at,
                    'metric_type': result.metric_type.value,
                    'details': result.details.model_dump_json() if result.details else None,
                    'prompt_tokens': result.prompt_tokens,
                    'completion_tokens': result.completion_tokens,
                    'latency_ms': result.latency_ms,
                    'span_id': span_id,
                    'metric_id': result.metric_id,
                })
        
        # Bulk insert metric results
        if metric_results_to_insert:
            stmt = insert(DatabaseMetricResult).values(metric_results_to_insert)
            self.db_session.execute(stmt)
            self.db_session.commit()
            
        logger.debug(f"Stored {len(metric_results_to_insert)} metric results")