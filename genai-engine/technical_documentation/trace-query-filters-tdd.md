# Technical Design Document: Advanced Trace Query Filters

## Overview

This technical design document outlines the implementation of advanced filtering capabilities for the **trace-level endpoints only**:
- `/v1/traces/query` 
- `/v1/traces/metrics/`

The `/v1/spans/query` endpoint will remain unchanged. These filters are designed to find **traces containing spans that match the filter criteria**, not individual spans.

## Phase 1: Schema Extensions

### 1.1 Create New Trace Query Request Schema ✅ COMPLETED
**Objective**: Create a dedicated schema for trace-level filtering (separate from span queries)

**Tasks**:
- [x] Create new `TraceQueryRequest` schema in both arthur-common and genai-engine
- [x] Keep existing `SpanQueryRequest` unchanged for `/v1/spans/query`
- [x] Implement comprehensive validation for trace-level filters
- [x] **ADDED**: Include `span_types` filter for span kind filtering

**Implemented schema** (located in `src/schemas/request_schemas.py`):
```python
class TraceQueryRequest(BaseModel):
    """Request schema for querying traces with comprehensive filtering."""
    
    # Required
    task_ids: list[str] = Field(..., description="Task IDs to filter on. At least one is required.", min_length=1)
    
    # Common optional filters
    trace_ids: Optional[list[str]] = Field(None, description="Trace IDs to filter on. Optional.")
    start_time: Optional[datetime] = Field(None, description="Inclusive start date in ISO8601 string format.")
    end_time: Optional[datetime] = Field(None, description="Exclusive end date in ISO8601 string format.")
    
    # Span-level filters
    tool_name: Optional[str] = Field(None, description="Return only results with this tool name.")
    span_types: Optional[list[str]] = Field(None, description="Span types to filter on. Optional.")
    
    # Query relevance filters
    query_relevance_eq: Optional[float] = Field(None, ge=0, le=1, description="Equal to this value.")
    query_relevance_gt: Optional[float] = Field(None, ge=0, le=1, description="Greater than this value.")
    query_relevance_gte: Optional[float] = Field(None, ge=0, le=1, description="Greater than or equal to this value.")
    query_relevance_lt: Optional[float] = Field(None, ge=0, le=1, description="Less than this value.")
    query_relevance_lte: Optional[float] = Field(None, ge=0, le=1, description="Less than or equal to this value.")
    
    # Response relevance filters  
    response_relevance_eq: Optional[float] = Field(None, ge=0, le=1, description="Equal to this value.")
    response_relevance_gt: Optional[float] = Field(None, ge=0, le=1, description="Greater than this value.")
    response_relevance_gte: Optional[float] = Field(None, ge=0, le=1, description="Greater than or equal to this value.")
    response_relevance_lt: Optional[float] = Field(None, ge=0, le=1, description="Less than this value.")
    response_relevance_lte: Optional[float] = Field(None, ge=0, le=1, description="Less than or equal to this value.")
    
    # Tool classification filters
    tool_selection: Optional[ToolClassEnum] = Field(None, description="Tool selection evaluation result.")
    tool_usage: Optional[ToolClassEnum] = Field(None, description="Tool usage evaluation result.")
    
    # Trace duration filters
    trace_duration_eq: Optional[float] = Field(None, ge=0, description="Duration exactly equal to this value (seconds).")
    trace_duration_gt: Optional[float] = Field(None, ge=0, description="Duration greater than this value (seconds).")
    trace_duration_gte: Optional[float] = Field(None, ge=0, description="Duration greater than or equal to this value (seconds).")
    trace_duration_lt: Optional[float] = Field(None, ge=0, description="Duration less than this value (seconds).")
    trace_duration_lte: Optional[float] = Field(None, ge=0, description="Duration less than or equal to this value (seconds).")
```

### 1.2 Implement Comprehensive Validation ✅ COMPLETED
**Objective**: Add robust validation for filter combinations

**Tasks**:
- [x] Create `@model_validator` for mutually exclusive filters
- [x] Implement comparison operator combination rules
- [x] Add detailed error messages matching spec requirements
- [x] **ADDED**: Field validators for relevance scores, trace duration, tool classification, and span_types

**Implemented validation** (in `src/schemas/request_schemas.py`):
```python
@model_validator(mode='after')
def validate_filter_combinations(self):
    """Validate that filter combinations are logically valid."""
    # Check mutually exclusive filters for each metric type
    for prefix in ['query_relevance', 'response_relevance', 'trace_duration']:
        eq_field = f"{prefix}_eq"
        comparison_fields = [f"{prefix}_{op}" for op in ['gt', 'gte', 'lt', 'lte']]
        
        if getattr(self, eq_field) and any(getattr(self, field) for field in comparison_fields):
            raise ValueError(f"{eq_field} cannot be combined with other {prefix} comparison operators")
            
        # Check for incompatible operator combinations
        if getattr(self, f"{prefix}_gt") and getattr(self, f"{prefix}_gte"):
            raise ValueError(f"Cannot combine {prefix}_gt with {prefix}_gte")
        if getattr(self, f"{prefix}_lt") and getattr(self, f"{prefix}_lte"):
            raise ValueError(f"Cannot combine {prefix}_lt with {prefix}_lte")

@field_validator("span_types")
@classmethod
def validate_span_types(cls, value: Optional[list[str]]) -> Optional[list[str]]:
    """Validate that all span_types are valid OpenInference span kinds."""
    if not value:
        return value
    
    # Get all valid span kind values
    valid_span_kinds = [kind.value for kind in OpenInferenceSpanKindValues]
    invalid_types = [st for st in value if st not in valid_span_kinds]
    
    if invalid_types:
        raise ValueError(
            f"Invalid span_types received: {invalid_types}. "
            f"Valid values: {', '.join(sorted(valid_span_kinds))}"
        )
    return value
```

## Phase 2: Database Layer Enhancements ✅ COMPLETED

### 2.1 Two-Phase Filtering Strategy ✅ COMPLETED
**Objective**: Implement efficient filtering that separates trace-level and span-level filters for optimal performance

**Filter Categories**:
- **Trace-Level Filters** (operate at trace level): `task_ids`, `trace_ids`, `start_time`, `end_time`, `trace_duration_filters`
- **Span-Level Filters** (find traces containing matching spans): `tool_name`, `span_types`, `query_relevance_filters`, `response_relevance_filters`, `tool_selection`, `tool_usage`

**Optimal Filter Order** (cheap to expensive):
1. `task_ids` (required, very fast index lookup)
2. `trace_ids` (if provided, very fast)
3. `start_time`/`end_time` (fast time range filtering)
4. `trace_duration_filters` (moderate cost - requires aggregation)
5. `tool_name` and `span_types` (moderate cost - span field queries)
6. `relevance_filters` (expensive - requires metric joins)
7. `tool_selection`/`tool_usage` (expensive - requires metric joins)


### 2.2 Phase 1: Trace-Level Filtering Implementation ✅ COMPLETED
**Objective**: Implement fast trace-level filters that operate on trace boundaries and duration

**Tasks**:
- [x] Basic trace filtering: `task_ids`, `trace_ids`, `start_time`, `end_time`
- [x] Trace duration filtering with aggregation and operator support
- [x] Optimized query structure for early filtering
- [x] **IMPLEMENTED**: Unified query strategy with JOINs and EXISTS conditions


### 2.3 Phase 2: Span-Level Filtering Implementation ✅ COMPLETED
**Objective**: Find traces containing spans that match ALL span-level criteria (expensive operations)

**Tasks**:
- [x] Tool name filtering: Query `span_name` where `span_kind = 'TOOL'`
- [x] **ADDED**: Span types filtering: Query `span_kind` for multiple span types
- [x] Metric filtering: Join with `metric_results` table for relevance scores using EXISTS conditions
- [x] Tool classification filtering: Query metric results for tool selection/usage scores
- [x] Handle cases where metrics don't exist (filter should exclude those spans)
- [x] Optimize metric joins using EXISTS subqueries for multiple filter types


### 2.4 Query Intersection and Optimization ✅ COMPLETED
**Objective**: Efficiently combine trace-level and span-level filtering results

**Tasks**:
- [x] Implement unified query strategy using JOINs and EXISTS
- [x] Optimize for cases with multiple metric filters using EXISTS subqueries
- [x] Handle edge cases where no traces match criteria
- [x] Database-level pagination for optimal performance


## Phase 3: Repository Layer Updates ✅ COMPLETED

### 3.1 Update SpanRepository Methods ✅ COMPLETED
**Objective**: Extend existing trace query methods to accept and use new filters

**Tasks**:
- [x] **IMPLEMENTED**: New `query_traces_with_filters` method accepting `TraceQueryRequest`
- [x] Maintain backward compatibility by keeping existing method signatures
- [x] Convert `TraceQueryRequest` to internal `TraceQuerySchema` format
- [x] Integration with optimized `SpanQueryService`

## Phase 4: API Layer Updates ✅ COMPLETED

### 4.1 Update Trace Endpoint Handlers ✅ COMPLETED
**Objective**: Modify only the trace endpoints to accept new filter parameters

**Tasks**:
- [x] Update `/v1/traces/query` endpoint parameters
- [x] Update `/v1/traces/metrics/` endpoint parameters  
- [x] Leave `/v1/spans/query` endpoint completely unchanged
- [x] Add comprehensive parameter validation
- [x] **IMPLEMENTED**: `trace_query_parameters` dependency function for parameter extraction
- [x] **ADDED**: Support for new `span_types` filter alongside existing filters

**Implemented route handlers** (in `src/routers/v1/span_routes.py`):
```python
def trace_query_parameters(
    # Required parameters
    task_ids: list[str] = Query(..., description="Task IDs to filter on. At least one is required.", min_length=1),
    # Optional parameters
    trace_ids: list[str] = Query(None, description="Trace IDs to filter on. Optional."),
    start_time: datetime = Query(None, description="Inclusive start date in ISO8601 string format."),
    end_time: datetime = Query(None, description="Exclusive end date in ISO8601 string format."),
    tool_name: str = Query(None, description="Return only results with this tool name."),
    span_types: list[str] = Query(None, description=f"Span types to filter on. Optional. Valid values: {', '.join(sorted([kind.value for kind in OpenInferenceSpanKindValues]))}"),
    # All relevance, tool classification, and duration filters...
    query_relevance_eq: float = Query(None, ge=0, le=1, description="Equal to this value."),
    # ... (all other filter parameters)
) -> TraceQueryRequest:
    """Create a TraceQueryRequest from query parameters."""
    return TraceQueryRequest(
        task_ids=task_ids,
        trace_ids=trace_ids,
        start_time=start_time,
        end_time=end_time,
        tool_name=tool_name,
        span_types=span_types,
        # ... all parameters
    )
```

### Backward Compatibility
- Existing `/v1/spans/query` endpoint remains completely unchanged
- Trace endpoints accept new optional parameters
- All existing functionality continues to work without modification
- Refactored query service maintains same public interface
