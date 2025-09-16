# Technical Design Document: ML Engine Trace Query Filters Implementation

## Overview

This technical design document outlines the **specific implementation changes** required in the **ML Engine** to support advanced trace query filtering for agentic datasets. The ML Engine will serve as a **validation and mapping layer** that forwards filters to the GenAI Engine, which contains all filtering business logic.

## Architecture Flow

```
Client Request → ML Engine (validate + map filters) → GenAI Engine (apply filters) → Results
                              ↓ (validation fails)
                         Error Response (no fallback)
```

## Current State vs. Target State

### Current ML Engine Implementation ❌ **ISSUES**
**File**: `src/ml_engine/connectors/shield_connector.py`

```python
# Line 135-138: BLOCKS all non-EQUALS operators
elif filter.op != DataResultFilterOp.EQUALS:
    self.logger.warning(
        f"Filter operation {filter.op} is not supported. Only {DataResultFilterOp.EQUALS} is supported for Shield Connector.",
    )

# Lines 224-232: GenAI Engine call has NO filter parameters
resp = self._spans_client.query_spans_v1_traces_query_get_with_http_info(
    task_ids=[dataset_locator_fields[SHIELD_DATASET_TASK_ID_FIELD]],
    trace_ids=None,  # Hardcoded
    start_time=start_time,
    end_time=end_time,
    page=params["page"],
    page_size=params["page_size"],
    sort=params.get(SHIELD_SORT_FILTER),
    # ❌ NO FILTER PARAMETERS PASSED
)
```

### Target ML Engine Implementation ✅ **TO BE BUILT**

**Supported Filter Mapping**:
```python
AGENTIC_FILTER_SUPPORT = {
    # Basic filters
    "trace_id": [DataResultFilterOp.EQUALS, DataResultFilterOp.IN],
    
    # Span-level filters  
    "tool_name": [DataResultFilterOp.EQUALS],
    "span_types": [DataResultFilterOp.IN, DataResultFilterOp.EQUALS],
    
    # Comparison filters
    "query_relevance": [DataResultFilterOp.EQUALS, DataResultFilterOp.GREATER_THAN,
                       DataResultFilterOp.GREATER_THAN_OR_EQUAL, DataResultFilterOp.LESS_THAN,
                       DataResultFilterOp.LESS_THAN_OR_EQUAL],
    "response_relevance": [DataResultFilterOp.EQUALS, DataResultFilterOp.GREATER_THAN,
                          DataResultFilterOp.GREATER_THAN_OR_EQUAL, DataResultFilterOp.LESS_THAN,
                          DataResultFilterOp.LESS_THAN_OR_EQUAL],
    "trace_duration": [DataResultFilterOp.EQUALS, DataResultFilterOp.GREATER_THAN,
                      DataResultFilterOp.GREATER_THAN_OR_EQUAL, DataResultFilterOp.LESS_THAN,
                      DataResultFilterOp.LESS_THAN_OR_EQUAL],
    
    # Exact match filters
    "tool_selection": [DataResultFilterOp.EQUALS],
    "tool_usage": [DataResultFilterOp.EQUALS],
}
```

---

## Technical Implementation Changes

### **Change 1: Fix Shield Connector Operator Restriction** 🚨 **CRITICAL**
**File**: `src/ml_engine/connectors/shield_connector.py`
**Lines**: 135-138

**Current Code (BROKEN)**:
```python
elif filter.op != DataResultFilterOp.EQUALS:
    self.logger.warning(
        f"Filter operation {filter.op} is not supported. Only {DataResultFilterOp.EQUALS} is supported for Shield Connector.",
    )
```

**Fix**: Replace with agentic filter validation
```python
elif not self._is_agentic_filter_supported(filter):
    self.logger.warning(
        f"Filter {filter.field_name} with operator {filter.op} is not supported.",
    )
```

### **Change 2: Add Agentic Filter Validation** 🆕 **NEW IMPLEMENTATION**
**File**: `src/ml_engine/connectors/shield_connector.py`
**Location**: Add new methods to `ShieldBaseConnector` class

**Add Constants**:
```python
# OpenInference span kinds (from openinference.semconv.trace import OpenInferenceSpanKindValues)
VALID_SPAN_KINDS = [
    "TOOL", "CHAIN", "LLM", "RETRIEVER", "EMBEDDING", 
    "AGENT", "RERANKER", "UNKNOWN", "GUARDRAIL", "EVALUATOR"
]

# Supported agentic filters
AGENTIC_FILTER_SUPPORT = {
    "trace_id": [DataResultFilterOp.EQUALS, DataResultFilterOp.IN],
    "tool_name": [DataResultFilterOp.EQUALS],
    "span_types": [DataResultFilterOp.IN, DataResultFilterOp.EQUALS],
    "query_relevance": [DataResultFilterOp.EQUALS, DataResultFilterOp.GREATER_THAN,
                       DataResultFilterOp.GREATER_THAN_OR_EQUAL, DataResultFilterOp.LESS_THAN,
                       DataResultFilterOp.LESS_THAN_OR_EQUAL],
    "response_relevance": [DataResultFilterOp.EQUALS, DataResultFilterOp.GREATER_THAN,
                          DataResultFilterOp.GREATER_THAN_OR_EQUAL, DataResultFilterOp.LESS_THAN,
                          DataResultFilterOp.LESS_THAN_OR_EQUAL],
    "trace_duration": [DataResultFilterOp.EQUALS, DataResultFilterOp.GREATER_THAN,
                      DataResultFilterOp.GREATER_THAN_OR_EQUAL, DataResultFilterOp.LESS_THAN,
                      DataResultFilterOp.LESS_THAN_OR_EQUAL],
    "tool_selection": [DataResultFilterOp.EQUALS],
    "tool_usage": [DataResultFilterOp.EQUALS],
}
```

**Add Validation Methods**:
```python
def _is_agentic_filter_supported(self, filter: DataResultFilter) -> bool:
    """Check if filter is supported for agentic datasets."""
    field_name = filter.field_name
    op = filter.op
    
    # Check if field is supported
    if field_name not in AGENTIC_FILTER_SUPPORT:
        return False
    
    # Check if operator is supported for this field
    return op in AGENTIC_FILTER_SUPPORT[field_name]

def _validate_agentic_filter(self, filter: DataResultFilter) -> None:
    """Validate agentic filter - raise errors for invalid filters."""
    field_name = filter.field_name
    op = filter.op
    value = filter.value
    
    # Check field/operator support
    if not self._is_agentic_filter_supported(filter):
        supported_ops = AGENTIC_FILTER_SUPPORT.get(field_name, [])
        raise ValueError(
            f"Filter '{field_name}' with operator '{op}' is not supported. "
            f"Supported operators for {field_name}: {supported_ops}" if supported_ops 
            else f"Filter field '{field_name}' is not supported for agentic datasets."
        )
    
    # Validate values
    self._validate_agentic_filter_value(field_name, value)

def _validate_agentic_filter_value(self, field_name: str, value: any) -> None:
    """Validate filter values with specific error messages."""
    if field_name in ["query_relevance", "response_relevance"]:
        if not isinstance(value, (int, float)) or not (0.0 <= value <= 1.0):
            raise ValueError(f"{field_name} must be a number between 0.0 and 1.0, got {value}")
    
    elif field_name == "trace_duration":
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"trace_duration must be a positive number, got {value}")
    
    elif field_name == "span_types":
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"span_types must be a list of strings, got {value}")
        
        invalid_types = [t for t in value if t not in VALID_SPAN_KINDS]
        if invalid_types:
            raise ValueError(f"Invalid span_types: {invalid_types}. Valid values: {VALID_SPAN_KINDS}")
    
    elif field_name in ["tool_selection", "tool_usage"]:
        if value not in [0, 1, 2]:
            raise ValueError(f"{field_name} must be 0, 1, or 2, got {value}")
```

### **Change 3: Add Parameter Mapping Logic** 🆕 **NEW IMPLEMENTATION**
**File**: `src/ml_engine/connectors/shield_connector.py`
**Location**: Add new methods to `ShieldBaseConnector` class

```python
def _map_agentic_filter_to_parameter(self, filter: DataResultFilter) -> tuple[str, any]:
    """Map DataResultFilter to GenAI Engine API parameter."""
    field_name = filter.field_name
    op = filter.op
    value = filter.value
    
    # Comparison field mapping (add operator suffix)
    if field_name in ["query_relevance", "response_relevance", "trace_duration"]:
        suffix_map = {
            DataResultFilterOp.EQUALS: "_eq",
            DataResultFilterOp.GREATER_THAN: "_gt", 
            DataResultFilterOp.GREATER_THAN_OR_EQUAL: "_gte",
            DataResultFilterOp.LESS_THAN: "_lt",
            DataResultFilterOp.LESS_THAN_OR_EQUAL: "_lte"
        }
        return f"{field_name}{suffix_map[op]}", value
    
    # Direct mapping fields
    elif field_name in ["span_types", "tool_name", "tool_selection", "tool_usage"]:
        return field_name, value
    
    # trace_id -> trace_ids conversion
    elif field_name == "trace_id":
        if op == DataResultFilterOp.EQUALS:
            return "trace_ids", [value] if isinstance(value, str) else value
        elif op == DataResultFilterOp.IN:
            return "trace_ids", value
    
    return None, None

def _build_agentic_filter_parameters(self, filters: list[DataResultFilter]) -> dict[str, any]:
    """Build GenAI Engine parameters from validated filters."""
    params = {}
    
    for filter in filters:
        param_name, param_value = self._map_agentic_filter_to_parameter(filter)
        if param_name and param_value is not None:
            params[param_name] = param_value
            self.logger.debug(f"Mapped filter {filter.field_name}:{filter.op} -> {param_name}:{param_value}")
    
    return params
```

### **Change 4: Update GenAI Engine API Call** 🔄 **MODIFY EXISTING**
**File**: `src/ml_engine/connectors/shield_connector.py`
**Lines**: 224-232

**Current Code (INCOMPLETE)**:
```python
resp = (
    self._spans_client.query_spans_v1_traces_query_get_with_http_info(
        task_ids=[dataset_locator_fields[SHIELD_DATASET_TASK_ID_FIELD]],
        trace_ids=None,  # Hardcoded!
        start_time=start_time,
        end_time=end_time,
        page=params["page"],
        page_size=params["page_size"],
        sort=params.get(SHIELD_SORT_FILTER),
    )
)
```

**Updated Code (WITH FILTERS)**:
```python
# Build filter parameters for agentic datasets
filter_params = {}
if is_agentic and filters:
    # Validate all filters first (raises errors if invalid)
    for filter in filters:
        self._validate_agentic_filter(filter)
    
    # Map to GenAI Engine parameters
    filter_params = self._build_agentic_filter_parameters(filters)
    self.logger.info(f"Applying {len(filter_params)} filter parameters to GenAI Engine")

resp = (
    self._spans_client.query_spans_v1_traces_query_get_with_http_info(
        task_ids=[dataset_locator_fields[SHIELD_DATASET_TASK_ID_FIELD]],
        start_time=start_time,
        end_time=end_time,
        page=params["page"],
        page_size=params["page_size"],
        sort=params.get(SHIELD_SORT_FILTER),
        
        # Add all mapped filter parameters
        **filter_params
    )
)
```

### **Change 5: Update Filter Validation Method** 🔄 **MODIFY EXISTING** 
**File**: `src/ml_engine/connectors/shield_connector.py`
**Method**: `_validate_filters` (lines 116-141)

**Current Logic**: Only supports basic Shield filters + EQUALS operator
**New Logic**: Support both basic Shield filters AND agentic filters

```python
def _validate_filters(
    self,
    filters: list[DataResultFilter],
    is_agentic: bool = False,
) -> list[DataResultFilter]:
    allowed_filters = []
    for filter in filters:
        try:
            if is_agentic:
                # For agentic datasets, validate against agentic filter support
                if filter.field_name in AGENTIC_FILTER_SUPPORT:
                    self._validate_agentic_filter(filter)
                    allowed_filters.append(filter)
                elif filter.field_name in SHIELD_ALLOWED_FILTERS.keys():
                    # Fall back to basic Shield validation for non-agentic filters
                    if self._validate_basic_shield_filter(filter):
                        allowed_filters.append(filter)
                else:
                    self.logger.warning(f"Filter field {filter.field_name} is not supported.")
            else:
                # For non-agentic datasets, use existing validation
                if self._validate_basic_shield_filter(filter):
                    allowed_filters.append(filter)
        except ValueError as e:
            # Convert validation errors to warnings for now (or raise based on requirements)
            self.logger.error(f"Filter validation failed: {e}")
            raise ValueError(f"Invalid filter: {e}")
    
    return allowed_filters

def _validate_basic_shield_filter(self, filter: DataResultFilter) -> bool:
    """Existing basic Shield filter validation."""
    if filter.field_name not in SHIELD_ALLOWED_FILTERS.keys():
        self.logger.warning(f"Filter field {filter.field_name} is not supported.")
        return False
    
    if not isinstance(filter.value, SHIELD_ALLOWED_FILTERS[filter.field_name]):
        self.logger.warning(
            f"Filter value for {filter.field_name} is of type {type(filter.value)}, "
            f"but should be of type {SHIELD_ALLOWED_FILTERS[filter.field_name]}."
        )
        return False
    
    if filter.op != DataResultFilterOp.EQUALS:
        self.logger.warning(
            f"Filter operation {filter.op} is not supported. "
            f"Only {DataResultFilterOp.EQUALS} is supported for non-agentic datasets."
        )
        return False
    
    return True
```

### **Change 6: Update Read Method Integration** 🔄 **MODIFY EXISTING**
**File**: `src/ml_engine/connectors/shield_connector.py` 
**Method**: `read` (around line 202-203)

**Current**: Calls `_validate_filters(filters)`
**Update**: Pass `is_agentic` flag to validation

```python
# Around line 202-203, update the validation call:
filters = self._validate_filters(filters, is_agentic=is_agentic)
```

---

## Summary of Technical Changes

### **Files Modified**:
1. **`src/ml_engine/connectors/shield_connector.py`** - Main implementation

### **Changes Required**:
1. ✅ **Remove operator restriction** (lines 135-138)
2. ✅ **Add agentic filter constants** (AGENTIC_FILTER_SUPPORT, VALID_SPAN_KINDS)
3. ✅ **Add validation methods** (_validate_agentic_filter, _validate_agentic_filter_value)
4. ✅ **Add parameter mapping** (_map_agentic_filter_to_parameter, _build_agentic_filter_parameters)
5. ✅ **Update GenAI Engine API call** (lines 224-232) to include filter parameters
6. ✅ **Update _validate_filters method** to handle agentic vs non-agentic datasets
7. ✅ **Update read method** to pass is_agentic flag to validation

### **No New Files Required**: All changes are contained within the existing shield connector.

---

## Testing Strategy

### **Unit Tests for Core Changes**
**File**: `tests/connectors/test_shield_connector.py`

```python
class TestAgenticFilterSupport:
    """Test the new agentic filter functionality."""
    
    def test_agentic_filter_validation(self):
        """Test individual filter validation."""
        connector = ShieldConnector(mock_config, mock_logger)
        
        # Valid filters
        valid_filter = DataResultFilter("query_relevance", DataResultFilterOp.GREATER_THAN_OR_EQUAL, 0.8)
        connector._validate_agentic_filter(valid_filter)  # Should not raise
        
        # Invalid field
        with pytest.raises(ValueError, match="not supported for agentic datasets"):
            invalid_filter = DataResultFilter("invalid_field", DataResultFilterOp.EQUALS, "value")
            connector._validate_agentic_filter(invalid_filter)
        
        # Invalid operator
        with pytest.raises(ValueError, match="not supported"):
            invalid_op = DataResultFilter("query_relevance", DataResultFilterOp.NOT_EQUALS, 0.8)
            connector._validate_agentic_filter(invalid_op)
        
        # Invalid value
        with pytest.raises(ValueError, match="must be a number between 0.0 and 1.0"):
            invalid_value = DataResultFilter("query_relevance", DataResultFilterOp.EQUALS, 1.5)
            connector._validate_agentic_filter(invalid_value)
    
    def test_parameter_mapping(self):
        """Test filter to parameter mapping."""
        connector = ShieldConnector(mock_config, mock_logger)
        
        # Comparison filter mapping
        filter = DataResultFilter("query_relevance", DataResultFilterOp.GREATER_THAN_OR_EQUAL, 0.8)
        param_name, param_value = connector._map_agentic_filter_to_parameter(filter)
        assert param_name == "query_relevance_gte"
        assert param_value == 0.8
        
        # trace_id conversion
        filter = DataResultFilter("trace_id", DataResultFilterOp.EQUALS, "trace-123")
        param_name, param_value = connector._map_agentic_filter_to_parameter(filter)
        assert param_name == "trace_ids"
        assert param_value == ["trace-123"]
    
    def test_full_pipeline_integration(self):
        """Test end-to-end filter processing."""
        # Mock the GenAI Engine API response
        with patch.object(connector._spans_client, 'query_spans_v1_traces_query_get_with_http_info') as mock_api:
            mock_api.return_value = Mock(raw_data='{"traces": []}')
            
            filters = [
                DataResultFilter("query_relevance", DataResultFilterOp.GREATER_THAN_OR_EQUAL, 0.8),
                DataResultFilter("span_types", DataResultFilterOp.IN, ["LLM", "TOOL"])
            ]
            
            result = connector.read(
                mock_agentic_dataset, 
                datetime.now(), 
                datetime.now(), 
                filters, 
                None
            )
            
            # Verify API was called with correct parameters
            mock_api.assert_called_once()
            call_kwargs = mock_api.call_args.kwargs
            assert "query_relevance_gte" in call_kwargs
            assert call_kwargs["query_relevance_gte"] == 0.8
            assert "span_types" in call_kwargs
            assert call_kwargs["span_types"] == ["LLM", "TOOL"]
```

### **Integration Tests**
**File**: `tests/job_executors/test_fetch_data_executor.py`

```python
def test_fetch_data_with_agentic_filters():
    """Test FetchDataExecutor with agentic filters."""
    job_spec = FetchDataJobSpec(
        dataset_id="agentic-dataset-123",
        start_timestamp=datetime(2024, 1, 1),
        end_timestamp=datetime(2024, 1, 31),
        data_filters=[
            DataResultFilter("query_relevance", DataResultFilterOp.GREATER_THAN_OR_EQUAL, 0.8),
            DataResultFilter("span_types", DataResultFilterOp.IN, ["LLM", "TOOL"])
        ],
        pagination_options=ConnectorPaginationOptions(page=1, page_size=100),
        operation_id="test-op-123"
    )
    
    # Mock dependencies and execute
    with patch.object(executor.connector_constructor, 'get_connector_from_spec'):
        executor.execute(job_spec)
        # Verify successful execution without errors
```

---

## Example Usage

### **Client Request Example**
```python
# Multi-filter agentic trace query
job_spec = FetchDataJobSpec(
    dataset_id="agentic-dataset-123",
    start_timestamp=datetime(2024, 1, 1),
    end_timestamp=datetime(2024, 1, 31),
    data_filters=[
        # Span filtering
        DataResultFilter("span_types", DataResultFilterOp.IN, ["LLM", "TOOL"]),
        DataResultFilter("tool_name", DataResultFilterOp.EQUALS, "web_search"),
        
        # Range filtering  
        DataResultFilter("query_relevance", DataResultFilterOp.GREATER_THAN_OR_EQUAL, 0.8),
        DataResultFilter("response_relevance", DataResultFilterOp.GREATER_THAN, 0.6),
        
        # Duration filtering
        DataResultFilter("trace_duration", DataResultFilterOp.GREATER_THAN_OR_EQUAL, 2.0),
        DataResultFilter("trace_duration", DataResultFilterOp.LESS_THAN, 30.0),
        
        # Tool classification
        DataResultFilter("tool_selection", DataResultFilterOp.EQUALS, 1)
    ],
    pagination_options=ConnectorPaginationOptions(page=1, page_size=100),
    operation_id="filtered-fetch-op"
)

# ML Engine processes and forwards to GenAI Engine
result = fetch_data_executor.execute(job_spec)
```

### **Error Handling Examples**
```python
# Invalid filter field
try:
    job_spec = FetchDataJobSpec(
        dataset_id="agentic-dataset-123",
        data_filters=[
            DataResultFilter("invalid_field", DataResultFilterOp.EQUALS, "value")
        ]
    )
    fetch_data_executor.execute(job_spec)
except ValueError as e:
    # Error: "Filter field 'invalid_field' is not supported for agentic datasets."
    
# Invalid operator combination  
try:
    job_spec = FetchDataJobSpec(
        dataset_id="agentic-dataset-123",
        data_filters=[
            DataResultFilter("query_relevance", DataResultFilterOp.NOT_EQUALS, 0.8)
        ]
    )
    fetch_data_executor.execute(job_spec)
except ValueError as e:
    # Error: "Filter 'query_relevance' with operator 'NOT_EQUALS' is not supported."

# Invalid value range
try:
    job_spec = FetchDataJobSpec(
        dataset_id="agentic-dataset-123", 
        data_filters=[
            DataResultFilter("query_relevance", DataResultFilterOp.EQUALS, 1.5)
        ]
    )
    fetch_data_executor.execute(job_spec)
except ValueError as e:
    # Error: "query_relevance must be a number between 0.0 and 1.0, got 1.5"
```

---

## Success Criteria

✅ **Functional Requirements**:
- Support all agentic filter types from GenAI Engine (span_types, relevance, duration, tool classification)
- Pre-validation of filters with clear error messages 
- Proper parameter mapping from DataResultFilter to GenAI Engine API
- Backward compatibility with existing non-agentic datasets
- No client-side fallback - fail fast with clear errors

✅ **Performance Requirements**:
- Filter validation < 50ms for typical filter sets
- API calls complete within existing SLA
- No additional memory overhead for non-agentic datasets

✅ **Quality Requirements**:
- Comprehensive error messages for invalid filters
- Full test coverage for new validation and mapping logic
- Clear documentation with usage examples
- Maintains existing shield connector interface

This TDD provides a complete technical implementation plan for adding agentic trace query filter support to the ML Engine as a validation and mapping layer that forwards requests to the GenAI Engine.