import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, asc, desc, select
from sqlalchemy.orm import Session

from db_models.db_models import DatabaseSpan, DatabaseTraceMetadata
from schemas.enums import PaginationSortMethod
from schemas.internal_schemas import Span
from utils import trace as trace_utils
from utils.constants import SPAN_KIND_LLM

logger = logging.getLogger(__name__)

# Constants
DEFAULT_PAGE_SIZE = 5


class SpanQueryService:
    """Service responsible for querying spans from the database."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_paginated_trace_metadata_for_task_ids(
        self,
        task_ids: list[str],
        trace_ids: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        page: int = 0,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> Optional[list[DatabaseTraceMetadata]]:
        """Get paginated trace metadata for given task IDs with proper ordering and filtering."""
        if not task_ids:
            return None

        # Query trace metadata table to get start/end times efficiently
        query = select(DatabaseTraceMetadata).where(
            DatabaseTraceMetadata.task_id.in_(task_ids),
        )

        # Optional filters
        if trace_ids:
            query = query.where(DatabaseTraceMetadata.trace_id.in_(trace_ids))
        if start_time:
            query = query.where(DatabaseTraceMetadata.start_time >= start_time)
        if end_time:
            query = query.where(DatabaseTraceMetadata.end_time <= end_time)

        # Efficient sorting with proper indexes
        if sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseTraceMetadata.start_time))
        else:
            query = query.order_by(asc(DatabaseTraceMetadata.start_time))

        # Pagination
        offset = page * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        results = self.db_session.execute(query).scalars().all()
        trace_metadata_result = list(results)

        logger.debug(
            f"Found {len(trace_metadata_result)} trace metadata records for task IDs: {task_ids} "
            f"(page={page}, page_size={page_size}, sort={sort})",
        )

        return trace_metadata_result if trace_metadata_result else None

    def query_spans_from_db(
        self,
        trace_ids: Optional[list[str]] = None,
        task_ids: Optional[list[str]] = None,
        span_types: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> list[Span]:
        """Query spans from database with given filters."""
        query = self._build_spans_query(
            trace_ids=trace_ids,
            task_ids=task_ids,
            span_types=span_types,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
        )

        # Apply pagination if provided
        if page is not None and page_size is not None:
            offset = page * page_size
            query = query.offset(offset).limit(page_size)

        results = self.db_session.execute(query).scalars().unique().all()
        return [Span._from_database_model(span) for span in results]

    def query_span_by_id(self, span_id: str) -> Optional[Span]:
        """Query a single span by span_id."""
        query = select(DatabaseSpan).where(DatabaseSpan.span_id == span_id)
        results = self.db_session.execute(query).scalars().unique().all()

        if not results:
            return None

        return Span._from_database_model(results[0])

    def validate_spans(self, spans: list[Span]) -> list[Span]:
        """Validate spans and return only valid ones."""
        valid_spans = []
        for span in spans:
            if trace_utils.validate_span_version(span.raw_data):
                valid_spans.append(span)
            else:
                logger.warning(
                    f"Skipping span {span.id} due to version validation failure",
                )
        return valid_spans

    def validate_span_for_metrics(self, span: Span, span_id: str):
        """Validate that a span can have metrics computed for it."""
        if span.span_kind != SPAN_KIND_LLM:
            raise ValueError(
                f"Span {span_id} is not an LLM span (span_kind: {span.span_kind})",
            )

        if not span.task_id:
            raise ValueError(f"Span {span_id} has no task_id")

    def _build_spans_query(
        self,
        trace_ids: Optional[list[str]] = None,
        task_ids: Optional[list[str]] = None,
        span_types: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
    ) -> select:
        """Build a query for spans with the given filters."""
        query = select(DatabaseSpan)

        # Build filter conditions
        conditions = []
        if trace_ids:
            conditions.append(DatabaseSpan.trace_id.in_(trace_ids))
        if task_ids:
            conditions.append(DatabaseSpan.task_id.in_(task_ids))
        if span_types:
            conditions.append(DatabaseSpan.span_kind.in_(span_types))
        if start_time:
            conditions.append(DatabaseSpan.start_time >= start_time)
        if end_time:
            conditions.append(DatabaseSpan.start_time <= end_time)

        # Apply filters if any conditions exist
        if conditions:
            query = query.where(and_(*conditions))

        # Apply sorting
        if sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseSpan.start_time))
        elif sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseSpan.start_time))

        return query
