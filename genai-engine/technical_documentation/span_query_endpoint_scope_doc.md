# Query Spans Functionality Implementation Specification

## Overview
The services refactor is complete. This specification covers the remaining changes needed to add the query spans functionality that supports span type filtering and span-level pagination.

## Pagination Strategy

### Trace-Level Pagination (Existing Endpoints)
All existing trace-related endpoints will continue to use trace-level pagination. This means:
- Page size refers to the number of traces returned
- Pagination is performed at the trace level first
- All spans within each paginated trace are returned
- Existing endpoints like `/traces/query` and `/traces/metrics` maintain this behavior

### Span-Level Pagination (New Endpoints)
The new span query endpoints will implement span-level pagination. This means:
- Page size refers to the number of individual spans returned
- Pagination is performed directly on spans, independent of their parent traces
- Spans are paginated based on their own attributes (timestamp, type, etc.)
- New endpoints like `/spans/query` use this approach

This dual approach ensures backward compatibility while providing more granular control for span-specific queries.

## 1. Span Repository Updates

### 1.1 Update `query_spans()` method signature in `src/repositories/span_repository.py`
**Current signature needs to be updated to add `span_types` parameter:**

```python
def query_spans(
    self,
    sort: PaginationSortMethod,
    page: int,
    page_size: int = DEFAULT_PAGE_SIZE,
    trace_ids: Optional[list[str]] = None,
    task_ids: Optional[list[str]] = None,
    span_types: Optional[list[str]] = None,  # ADD THIS PARAMETER
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    include_metrics: bool = False,
    compute_new_metrics: bool = True,
) -> list[Span]:
```

### 1.2 Update query logic to support span-level pagination
**Change the implementation to support direct span querying instead of trace-based querying:**

```python
# Replace the current trace-based approach with direct span querying
spans = self.span_query_service.query_spans_from_db(
    trace_ids=trace_ids,
    task_ids=task_ids,
    span_types=span_types,  # Add this parameter
    start_time=start_time,
    end_time=end_time,
    sort=sort,
    page=page,          # Add pagination at span level
    page_size=page_size, # Add pagination at span level
)
```

### 1.3 Add span type validation
**Add validation call in the `query_spans()` method:**

```python
# Add after parameter validation
trace_utils.validate_span_types(span_types)
```

## 2. Span Query Service Updates  

### 2.1 Update `query_spans_from_db()` method in `src/services/span_query_service.py`
**Add missing parameters and functionality:**

```python
def query_spans_from_db(
    self,
    trace_ids: Optional[list[str]] = None,
    task_ids: Optional[list[str]] = None,  # ADD THIS
    span_types: Optional[list[str]] = None,  # ADD THIS  
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
    page: Optional[int] = None,  # ADD THIS
    page_size: Optional[int] = None,  # ADD THIS
) -> list[Span]:
```

### 2.2 Update `_build_spans_query()` method
**Add support for task_ids and span_types filtering:**

```python
def _build_spans_query(
    self,
    trace_ids: Optional[list[str]] = None,
    task_ids: Optional[list[str]] = None,  # ADD THIS
    span_types: Optional[list[str]] = None,  # ADD THIS
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
) -> select:
    # Add conditions for task_ids and span_types
    if task_ids:
        conditions.append(DatabaseSpan.task_id.in_(task_ids))
    if span_types:
        conditions.append(DatabaseSpan.span_kind.in_(span_types))
```

## 3. New API Endpoint

### 3.1 Add new endpoint to `src/routers/v1/span_routes.py`

```python
@span_routes.get(
    "/spans/query",
    description="Query spans filtered by span type. Task IDs are required. Returns spans with any existing metrics but does not compute new ones.",
    response_model=QuerySpansResponse,
    response_model_exclude_none=True,
    tags=["Spans"],
    responses={
        400: {"description": "Invalid span types or parameters"},
        404: {"description": "No spans found"},
        422: {"description": "Validation error"},
    }
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def query_spans_by_type(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    task_ids: list[str] = Query(
        ...,
        description="Task IDs to filter on. At least one is required.",
        min_length=1,
    ),
    span_types: list[str] = Query(
        None,
        description=f"Span types to filter on. Optional. Valid values: {', '.join(sorted([kind.value for kind in OpenInferenceSpanKindValues]))}",
    ),
    start_time: datetime = Query(
        None,
        description="Inclusive start date in ISO8601 string format.",
    ),
    end_time: datetime = Query(
        None,
        description="Exclusive end date in ISO8601 string format.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
```

### 3.2 Add required import
```python
from openinference.semconv.trace import OpenInferenceSpanKindValues
```

### 3.3 Update existing method call in `compute_span_metrics()`
**Change line 228:**
```python
# FROM:
return span._to_metrics_response_model()
# TO:  
return span._to_response_model()
```

## 4. Schema Updates

### 4.1 Update `src/schemas/response_schemas.py`
**Remove deprecated classes and update QuerySpansResponse:**

```python
# REMOVE these classes:
# - SpanResponse 
# - ComputeMetricsFiltersResponse
# - ComputeMetricsResponse

# UPDATE QuerySpansResponse to use SpanWithMetricsResponse:
class QuerySpansResponse(BaseModel):
    count: int = Field(
        description="The total number of spans matching the query parameters",
    )
    spans: list[SpanWithMetricsResponse] = Field(  # CHANGED from SpanResponse
        description="List of spans with metrics matching the search filters",
    )
```

### 4.2 Update `src/schemas/internal_schemas.py`
**Remove old method and rename existing one:**

```python
# REMOVE this method:
def _to_response_model(self) -> SpanResponse:
    # ... remove entire method

# RENAME this method:
# FROM: _to_metrics_response_model
# TO:   _to_response_model  
def _to_response_model(self) -> SpanWithMetricsResponse:  # Keep existing implementation
```

### 4.3 Update imports in internal_schemas.py
**Remove SpanResponse from imports:**
```python
# REMOVE SpanResponse from this import:
from schemas.response_schemas import (
    # ... other imports ...
    # SpanResponse,  # REMOVE THIS LINE
    SpanWithMetricsResponse,
    # ... other imports ...
)
```

## 5. Utility Function Updates

### 5.1 Add to `src/utils/trace.py`
```python
def validate_span_types(span_types: list[str]) -> None:
    """
    Validate that all span_types are valid OpenInference span kinds.
    
    Args:
        span_types: List of span type strings to validate
        
    Raises:
        ValueError: If any span types are invalid
    """
    if not span_types:
        return
        
    from openinference.semconv.trace import OpenInferenceSpanKindValues
    
    invalid_span_types = [
        st for st in span_types if st not in OpenInferenceSpanKindValues
    ]
    
    if invalid_span_types:
        raise ValueError(f"Invalid span_types received: {invalid_span_types}.")
```

## 6. Dependency Updates

### 6.1 Update `pyproject.toml`
```toml
# ADD this line:
openinference-semantic-conventions = "^0.1.12"
```

### 6.2 Update lock file
```bash
poetry lock
```

## 7. Test Updates

### 7.1 Create `tests/routes/span/test_query_spans.py`
- **Purpose**: Test the new query spans endpoint
- **Coverage**: Span type filtering, pagination, validation, error cases
- **Edge Cases**: 
  - Empty span_types list
  - None span_types
  - Maximum span_types limit
  - Case sensitivity
  - Invalid span types
  - Various parameter combinations

### 7.2 Update `tests/clients/base_test_client.py`
```python
# ADD import:
from schemas.response_schemas import QuerySpansResponse

# ADD method:
def query_spans(
    self,
    task_ids: list[str],
    span_types: list[str] | None = None,
    # ... other parameters
) -> tuple[int, QuerySpansResponse | str]:
```

### 7.3 Update `tests/routes/span/test_span_routes.py`
```python
# UPDATE mock path:
# FROM: "repositories.span_repository.get_metrics_engine"  
# TO:   "services.metrics_integration_service.get_metrics_engine"
```

## 8. Missing Method in SpanQueryService

### 8.1 Move validation method from SpanRepository 
**The `validate_span_for_metrics` method needs to be added to `SpanQueryService` if it's being called from SpanRepository line 125.**

Either:
1. Move the method from `MetricsIntegrationService` to `SpanQueryService`, or  
2. Update SpanRepository line 125 to call `self.metrics_integration_service.validate_span_for_metrics()`

## Implementation Priority

1. **Update SpanQueryService** - Add missing parameters and span-level pagination
2. **Update SpanRepository** - Add span_types parameter and update query logic  
3. **Add utility function** - span type validation with edge case handling
4. **Update schemas** - Remove deprecated classes, update response models
5. **Add new API endpoint** - with proper validation and response handling
6. **Update dependencies** - Add OpenInference semantic conventions
7. **Create tests** - Comprehensive test coverage including edge cases

## Key Differences from Original Spec

- **Services already exist** - Focus only on missing functionality
- **Method signature changes** - Update existing methods rather than create new ones
- **Response model consolidation** - Remove separate span/metrics responses  
- **Dual Pagination Strategy** - Existing trace endpoints maintain trace-level pagination while new span endpoints implement span-level pagination for more granular control
- **Validation integration** - Add span type validation to existing flow
- **Edge case handling** - Added comprehensive validation and error handling
- **Breaking changes** - Confirmed safe to remove/modify specified classes

Note: Database optimizations will be handled in a separate MR.