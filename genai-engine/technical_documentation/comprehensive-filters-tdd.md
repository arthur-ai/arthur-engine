# Technical Design Document: Comprehensive Query Filters Architecture

This TDD documents the **completed implementation** of a comprehensive filtering architecture for both trace-based and span-based queries across the GenAI Engine API endpoints.

**Key Achievements**:
- Unified `FilterService` providing reusable filtering components for all query patterns
- Enhanced `/api/v1/traces` endpoints with comprehensive filtering capabilities
- Enhanced `/api/v1/spans` endpoints with identical filtering logic and parameters
- Maintained 100% backward compatibility with existing APIs
- Single-query architecture eliminating performance bottlenecks
- Database-agnostic implementation supporting PostgreSQL and SQLite

## Overview

This comprehensive filtering architecture in the GenAI Engine implements a unified, modular approach to query filtering that supports multiple query patterns in different contexts with consistent filter logic.

### Core Problem Statement

**Performance Concerns Addressed**:
- **Multiple Database Round-trips**: Original implementation required separate queries for different filter types
- **Application-level Filtering**: Expensive post-query filtering in Python instead of database-level filtering
- **Inconsistent Query Patterns**: Different endpoints used different filtering approaches
- **Poor Scalability**: Query performance degraded significantly with complex filter combinations

**Usability Concerns Addressed**:
- **Inconsistent Filter Parameters**: Different endpoints supported different filter sets
- **Limited Filter Combinations**: Complex queries required multiple API calls
- **Lack of Span-level Filtering**: No way to find individual spans matching criteria
- **Poor Filter Discoverability**: No clear documentation of supported filter combinations

## Architecture Overview

### Unified Filter Patterns

The implementation supports two distinct but logically identical query patterns:

#### 1. Trace-Based Filtering
- **Purpose**: Find traces containing spans that match criteria
- **Endpoints**: `/api/v1/traces` and `/v1/traces/query (deprecated)`
- **Returns**: Trace metadata for traces containing matching spans
- **Use Case**: "Show me all conversation traces that used the search tool"

#### 2. Span-Based Filtering  
- **Purpose**: Find individual spans that match criteria
- **Endpoints**: `/api/v1/spans`
- **Returns**: Individual span objects that match the criteria
- **Use Case**: "Show me all spans that used the search tool and LLM spans with high relevance"

### Core Design Principles

#### Unified Filter Logic
**Both filtering approaches use identical logical composition rules**:
- **AND within span kinds**: All conditions for a specific span kind must match
- **OR across span kinds**: Results include spans/traces matching ANY of the requested span kinds
- **Auto-discovery**: If no `span_types` specified, auto-detect from filter types

#### Single-Query Architecture
**Each operation uses exactly one composite database query**:
- All filtering logic applied at database level
- Single query serves both count and paginated results
- Eliminates multiple round-trips and application-level filtering

#### Modular Component Reuse
**Shared `FilterService` provides reusable components**:
- Same validation logic for both trace-based and span-based patterns
- Database-specific abstractions for PostgreSQL and SQLite
- Consistent filter composition and compatibility checking

## Filter Parameters Implementation

### Complete Filter Set
All endpoints now support the comprehensive filter parameter set:

**Basic Filters**:
- `task_ids` (required): Task IDs to filter on
- `trace_ids`: Specific trace IDs to filter on
- `start_time` / `end_time`: Time range filtering
- `span_types`: Span kinds to filter on (AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN)

**Tool Filters**:
- `tool_name`: Filter by specific tool name (requires TOOL spans)

**Relevance Score Filters** (0-1 range):
- `query_relevance_*`: Query relevance scoring (eq/gt/gte/lt/lte)
- `response_relevance_*`: Response relevance scoring (eq/gt/gte/lt/lte)

**Tool Classification Filters**:
- `tool_selection`: Tool selection evaluation (INCORRECT=0, CORRECT=1, NA=2)
- `tool_usage`: Tool usage evaluation (INCORRECT=0, CORRECT=1, NA=2)

**Trace Duration Filters**:
- `trace_duration_*`: Duration filtering in seconds (eq/gt/gte/lt/lte)

### Filter Combination Rules

#### Core Logic: AND within span types, OR across span types

**Within Span Type**: All conditions must match
```sql
-- Example: LLM spans with high relevance AND correct tool selection
(span_kind = 'LLM' AND query_relevance > 0.8 AND tool_selection = 1)
```

**Across Span Types**: Match ANY span type
```sql
-- Example: High-relevance LLM spans OR search tool spans
(span_kind = 'LLM' AND query_relevance > 0.8) 
OR 
(span_kind = 'TOOL' AND span_name = 'search')
```

#### Auto-Detection and Validation

**Span Type Auto-Detection**:
- LLM metric filters → automatically includes LLM spans
- `tool_name` filter → automatically includes TOOL spans
- No manual `span_types` specification required

**Compatibility Validation**:
- LLM metrics on TOOL spans → returns empty results
- Tool names on LLM spans → returns empty results  
- Incompatible combinations logged as warnings but don't error

## Implementation Architecture

### FilterService: Shared Component Library

**Purpose**: Central service containing all reusable filtering logic

**Core Methods**:
```python
class FilterService:
    # Validation and Detection
    def auto_detect_span_types(filters) -> List[str]
    def validate_filter_compatibility(filters) -> List[str]
    
    # Database Abstraction
    def extract_json_field(column, *path_components)  # PostgreSQL/SQLite compatible
    def build_comparison_condition(column, filter_item)
    
    # Query Building Components
    def build_single_span_type_conditions(span_type, filters) -> List
    def build_multiple_span_types_or_conditions(span_types, filters) -> List
    def build_all_metric_exists_conditions(filters, correlation_column) -> List
    def build_span_metric_exists_conditions(filters, span_id_column) -> List
```

**Key Features**:
- Database-agnostic JSON extraction for PostgreSQL JSONB and SQLite JSON
- Optimized EXISTS clause generation for metric filtering
- Comprehensive validation with detailed compatibility checking
- Consistent AND/OR logic composition for both query patterns

### SpanQueryService: Enhanced Query Engine

**Purpose**: Enhanced service supporting both filtering patterns using FilterService components

**Trace-Based Query Methods**:
```python
def get_paginated_trace_ids_with_filters(filters, pagination) -> (List[str], int)
def _build_unified_trace_query(filters) -> select  # Single composite query
def _apply_trace_level_filters(query, filters) -> select
def _apply_span_level_filters_with_joins(query, filters) -> select
```

**Span-Based Query Methods** (New):
```python
def get_paginated_spans_with_filters(filters, pagination) -> (List[Span], int)
def _build_unified_span_query(filters) -> select  # Single composite query  
def _apply_span_level_filters_direct(query, filters) -> select
def _apply_trace_filters_with_join(query, filters) -> select
```

**Optimization Strategies**:
- **Single vs Multiple Span Types**: Different optimization paths based on span type count
- **JOIN vs EXISTS**: JOINs for simple filters, EXISTS for complex metric filters
- **Index-first Filtering**: Task IDs and trace metadata leverage existing indexes
- **Database-level Pagination**: LIMIT/OFFSET applied at database layer

### SpanRepository: Dual-Mode Operation

**Purpose**: Seamless integration maintaining backward compatibility

**Enhanced Method**:
```python
def query_spans(
    # ... existing parameters
    filters: Optional[TraceQueryRequest] = None,  # NEW: Comprehensive filtering
) -> tuple[list[Span], int]:
```

## Performance Optimizations Implemented

### Single Composite Query Architecture

**Problem Solved**: Eliminated multiple database round-trips
```python
# OLD: Multiple queries
trace_ids = query_traces_by_basic_filters()
filtered_trace_ids = query_traces_by_span_filters(trace_ids)  
final_trace_ids = query_traces_by_metric_filters(filtered_trace_ids)
spans = query_spans_by_trace_ids(final_trace_ids)

# NEW: Single composite query
spans, count = service.get_paginated_spans_with_filters(filters, pagination)
```

**Benefits**:
- **Query Count**: Reduced from 3-5 queries to 1 query per operation
- **Database Optimization**: Query planner optimizes entire composite operation
- **Consistent Performance**: Predictable execution time regardless of filter complexity
- **Memory Efficiency**: Single result set, no intermediate collections

### Database-Specific Optimizations

**PostgreSQL Optimizations**:
```python
# JSONB extraction for metrics
func.jsonb_extract_path_text(column, 'query_relevance', 'llm_relevance_score')
# Array aggregation for sessions
func.array_agg(DatabaseTraceMetadata.trace_id)
```

**SQLite Optimizations (For Tests)**:
```python  
# JSON extraction for metrics
func.json_extract(column, '$.query_relevance.llm_relevance_score')
# String aggregation for sessions  
func.group_concat(DatabaseTraceMetadata.trace_id)
```

## API Enhancement Implementation

### Shared Parameter Injection

**Implementation**: Both endpoints use `trace_query_parameters` dependency
```python
def trace_query_parameters(
    task_ids: list[str] = Query(...),
    trace_ids: list[str] = Query(None),
    # ... all filter parameters
    query_relevance_gte: float = Query(None, ge=0, le=1),
    tool_selection: ToolClassEnum = Query(None),
    # ... etc
) -> TraceQueryRequest:
```

**Benefits**:
- **Single Definition**: All parameters defined once, used by both endpoints
- **Consistent Validation**: Same validation rules across endpoints
- **OpenAPI Generation**: Automatic API documentation for all parameters
- **Type Safety**: Full Pydantic validation with detailed error messages

