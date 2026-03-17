# TraceMetadataResponse

Lightweight trace metadata for list operations

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**prompt_token_count** | **int** |  | [optional] 
**completion_token_count** | **int** |  | [optional] 
**total_token_count** | **int** |  | [optional] 
**prompt_token_cost** | **float** |  | [optional] 
**completion_token_cost** | **float** |  | [optional] 
**total_token_cost** | **float** |  | [optional] 
**trace_id** | **str** | ID of the trace | 
**task_id** | **str** | Task ID this trace belongs to | 
**user_id** | **str** |  | [optional] 
**session_id** | **str** |  | [optional] 
**start_time** | **datetime** | Start time of the earliest span | 
**end_time** | **datetime** | End time of the latest span | 
**span_count** | **int** | Number of spans in this trace | 
**duration_ms** | **float** | Total trace duration in milliseconds | 
**created_at** | **datetime** | When the trace was first created | 
**updated_at** | **datetime** | When the trace was last updated | 
**input_content** | **str** |  | [optional] 
**output_content** | **str** |  | [optional] 
**annotations** | [**List[AgenticAnnotationResponse]**](AgenticAnnotationResponse.md) |  | [optional] 
**spans** | [**List[SpanWithMetricsResponse]**](SpanWithMetricsResponse.md) |  | [optional] 

## Example

```python
from _generated.models.trace_metadata_response import TraceMetadataResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TraceMetadataResponse from a JSON string
trace_metadata_response_instance = TraceMetadataResponse.from_json(json)
# print the JSON string representation of the object
print(TraceMetadataResponse.to_json())

# convert the object into a dict
trace_metadata_response_dict = trace_metadata_response_instance.to_dict()
# create an instance of TraceMetadataResponse from a dict
trace_metadata_response_from_dict = TraceMetadataResponse.from_dict(trace_metadata_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


