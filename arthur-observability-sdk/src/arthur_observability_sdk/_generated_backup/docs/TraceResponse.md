# TraceResponse

Response model for a single trace containing nested spans

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
**start_time** | **datetime** | Start time of the earliest span in this trace | 
**end_time** | **datetime** | End time of the latest span in this trace | 
**input_content** | **str** |  | [optional] 
**output_content** | **str** |  | [optional] 
**root_spans** | [**List[NestedSpanWithMetricsResponse]**](NestedSpanWithMetricsResponse.md) | Root spans (spans with no parent) in this trace, with children nested | [optional] [default to []]
**annotations** | [**List[AgenticAnnotationResponse]**](AgenticAnnotationResponse.md) |  | [optional] 

## Example

```python
from _generated.models.trace_response import TraceResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TraceResponse from a JSON string
trace_response_instance = TraceResponse.from_json(json)
# print the JSON string representation of the object
print(TraceResponse.to_json())

# convert the object into a dict
trace_response_dict = trace_response_instance.to_dict()
# create an instance of TraceResponse from a dict
trace_response_from_dict = TraceResponse.from_dict(trace_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


