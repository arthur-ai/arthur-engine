# Technical Design Document: Targeted API Endpoints for Performance Optimization

## Overview

This technical design document outlines the implementation of new lightweight, targeted API endpoints that separate data retrieval from metrics computation. These endpoints are designed to improve UI performance by providing fast metadata-only endpoints for browsing/filtering operations, with separate on-demand endpoints for expensive operations like metrics computation.

## Objectives

1. **Performance Optimization**: Provide fast metadata-only endpoints for UI browsing operations
2. **Separation of Concerns**: Separate data retrieval from metrics computation operations
3. **Granular Control**: Enable targeted operations at span, trace, and session levels
4. **Backward Compatibility**: Maintain existing endpoints unchanged while adding new capabilities
5. **Caching Efficiency**: Enable lightweight responses that can be cached more aggressively

## API Specification

### New Endpoints Overview

| Endpoint | Purpose | Response Type | Metrics |
|----------|---------|---------------|---------|
| `GET /api/v1/traces` | Trace browsing/filtering | Trace metadata only | No |
| `GET /api/v1/traces/{trace_id}` | Single trace detail | Full trace tree | Existing |
| `GET /api/v1/traces/{trace_id}/metrics` | Compute missing trace metrics | Full trace tree | All |
| `GET /api/v1/spans` | Span browsing/filtering | Span metadata only | No |
| `GET /api/v1/spans/{span_id}` | Single span detail | Full span object | Existing |
| `GET /api/v1/spans/{span_id}/metrics` | Compute missing span metrics | Span with metrics | All |
| `GET /api/v1/sessions` | Session browsing | Session metadata | No |
| `GET /api/v1/sessions/{session_id}` | Session traces | List of trace trees | No |
| `GET /api/v1/sessions/{session_id}/metrics` | Compute missing session metrics | List of trace trees | All |

## Phase 1: Response Model Creation

### 1.1 Lightweight Metadata Response Models

**File**: `src/schemas/response_schemas.py` (UPDATE EXISTING FILE)

Add to the existing response schemas file. First, update the imports:

```python
from datetime import datetime
from typing import List, Optional

from arthur_common.models.response_schemas import ExternalInference, TraceResponse
from pydantic import BaseModel, Field

# ... existing classes remain unchanged ...
```

Then add the new lightweight response models:

```python
class TraceMetadataResponse(BaseModel):
    """Lightweight trace metadata for list operations"""
    trace_id: str = Field(description="ID of the trace")
    task_id: str = Field(description="Task ID this trace belongs to")
    session_id: Optional[str] = Field(None, description="Session ID if available")
    start_time: datetime = Field(description="Start time of the earliest span")
    end_time: datetime = Field(description="End time of the latest span")
    span_count: int = Field(description="Number of spans in this trace")
    duration_seconds: float = Field(description="Total trace duration in seconds")
    created_at: datetime = Field(description="When the trace was first created")
    updated_at: datetime = Field(description="When the trace was last updated")


class SpanMetadataResponse(BaseModel):
    """Lightweight span metadata for list operations"""
    id: str = Field(description="Internal database ID")
    trace_id: str = Field(description="ID of the parent trace")
    span_id: str = Field(description="OpenTelemetry span ID")
    parent_span_id: Optional[str] = Field(None, description="Parent span ID")
    span_kind: Optional[str] = Field(None, description="Type of span (LLM, TOOL, etc.)")
    span_name: Optional[str] = Field(None, description="Human-readable span name")
    start_time: datetime = Field(description="Span start time")
    end_time: datetime = Field(description="Span end time")
    task_id: Optional[str] = Field(None, description="Task ID this span belongs to")
    session_id: Optional[str] = Field(None, description="Session ID if available")
    status_code: str = Field(description="Status code (Unset, Error, Ok)")
    created_at: datetime = Field(description="When the span was created")
    updated_at: datetime = Field(description="When the span was updated")
    # Note: Excludes raw_data, computed features, and metrics for performance


class SessionMetadataResponse(BaseModel):
    """Session summary metadata"""
    session_id: str = Field(description="Session identifier")
    task_ids: list[str] = Field(description="Unique task IDs in this session")
    trace_count: int = Field(description="Number of traces in this session")
    span_count: int = Field(description="Total number of spans in this session")
    earliest_start_time: datetime = Field(description="Start time of earliest trace")
    latest_end_time: datetime = Field(description="End time of latest trace")
    duration_seconds: float = Field(description="Total session duration in seconds")


class TraceListResponse(BaseModel):
    """Response for trace list endpoint"""
    count: int = Field(description="Total number of traces matching filters")
    traces: list[TraceMetadataResponse] = Field(description="List of trace metadata")


class SpanListResponse(BaseModel):
    """Response for span list endpoint"""
    count: int = Field(description="Total number of spans matching filters")
    spans: list[SpanMetadataResponse] = Field(description="List of span metadata")


class SessionListResponse(BaseModel):
    """Response for session list endpoint"""
    count: int = Field(description="Total number of sessions matching filters")
    sessions: list[SessionMetadataResponse] = Field(description="List of session metadata")


class SessionTracesResponse(BaseModel):
    """Response for session traces endpoint"""
    session_id: str = Field(description="Session identifier")
    count: int = Field(description="Number of traces in this session")
    traces: list[TraceResponse] = Field(description="List of full trace trees")
```

### 1.2 Internal Schema Extensions

**File**: `src/schemas/internal_schemas.py`

Add conversion methods to existing models:

```python
class TraceMetadata(BaseModel):
    # ... existing fields ...
    
    def _to_metadata_response_model(self) -> TraceMetadataResponse:
        """Convert to lightweight metadata response"""
        duration_seconds = (self.end_time - self.start_time).total_seconds()
        return TraceMetadataResponse(
            trace_id=self.trace_id,
            task_id=self.task_id,
            session_id=self.session_id,
            start_time=self.start_time,
            end_time=self.end_time,
            span_count=self.span_count,
            duration_seconds=duration_seconds,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class Span(BaseModel):
    # ... existing fields ...
    
    def _to_metadata_response_model(self) -> SpanMetadataResponse:
        """Convert to lightweight metadata response"""
        return SpanMetadataResponse(
            id=self.id,
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            span_kind=self.span_kind,
            span_name=self.span_name,
            start_time=self.start_time,
            end_time=self.end_time,
            task_id=self.task_id,
            session_id=self.session_id,
            status_code=self.status_code,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
```

## Phase 2: Service Extensions Required

### 2.1 SpanRepository Changes

**File**: `src/repositories/span_repository.py`

Add the following new methods:

- `get_traces_metadata()` - Return trace metadata only without spans or metrics
- `get_trace_by_id()` - Get complete trace tree with existing metrics (no computation)
- `get_spans_metadata()` - Return span metadata only without raw data or metrics
- `get_span_by_id()` - Get single span with existing metrics (no computation)
- `compute_trace_metrics()` - Compute all missing metrics for trace spans on-demand
- `get_sessions_metadata()` - Return session aggregation data
- `get_session_traces()` - Get all trace trees in a session
- `compute_session_metrics()` - Compute all missing metrics for session traces on-demand

### 2.2 SpanQueryService Changes

**File**: `src/services/span_query_service.py`

Add the following new methods:

- `get_trace_metadata_by_ids()` - Query trace metadata table directly by trace IDs
- `get_sessions_aggregated()` - Perform session-level aggregations with filtering
- `get_trace_ids_for_session()` - Get paginated trace IDs for a specific session

### 2.3 Add SessionMetadata Schema

**File**: `src/schemas/internal_schemas.py`

```python
class SessionMetadata(BaseModel):
    """Internal session metadata representation"""
    session_id: str
    task_ids: list[str]
    trace_count: int
    span_count: int
    earliest_start_time: datetime
    latest_end_time: datetime
    duration_seconds: float
    
    def _to_metadata_response_model(self) -> SessionMetadataResponse:
        """Convert to API response model"""
        return SessionMetadataResponse(
            session_id=self.session_id,
            task_ids=self.task_ids,
            trace_count=self.trace_count,
            span_count=self.span_count,
            earliest_start_time=self.earliest_start_time,
            latest_end_time=self.latest_end_time,
            duration_seconds=self.duration_seconds,
        )
```

## Phase 3: API Route Implementation

### 3.1 Create New Trace API Routes File

**File**: `src/routers/v1/trace_api_routes.py` (CREATE NEW FILE)

Create new FastAPI router with `/api/v1` prefix for all new endpoints:

**TRACE ENDPOINTS:**
- `GET /api/v1/traces` - List trace metadata with pagination and filtering
- `GET /api/v1/traces/{trace_id}` - Get single trace tree with existing metrics
- `GET /api/v1/traces/{trace_id}/metrics` - Compute missing trace metrics on-demand

**SPAN ENDPOINTS:**
- `GET /api/v1/spans` - List span metadata with pagination and filtering  
- `GET /api/v1/spans/{span_id}` - Get single span with existing metrics
- `GET /api/v1/spans/{span_id}/metrics` - Compute missing span metrics on-demand

**SESSION ENDPOINTS:**
- `GET /api/v1/sessions` - List session metadata with pagination and filtering
- `GET /api/v1/sessions/{session_id}` - Get all traces in a session
- `GET /api/v1/sessions/{session_id}/metrics` - Compute missing session metrics on-demand


### 3.2 Dependencies Required

- Reuse existing `trace_query_parameters` function
- Use existing authentication, pagination, and permission checking utilities
- Repository dependency injection pattern
- Add imports for new response schemas: `TraceListResponse`, `SpanListResponse`, `SessionListResponse`, `SessionTracesResponse`
