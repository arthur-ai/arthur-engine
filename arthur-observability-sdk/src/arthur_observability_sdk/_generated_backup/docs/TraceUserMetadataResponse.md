# TraceUserMetadataResponse

User summary metadata in trace context

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**prompt_token_count** | **int** |  | [optional] 
**completion_token_count** | **int** |  | [optional] 
**total_token_count** | **int** |  | [optional] 
**prompt_token_cost** | **float** |  | [optional] 
**completion_token_cost** | **float** |  | [optional] 
**total_token_cost** | **float** |  | [optional] 
**user_id** | **str** | User identifier | 
**task_id** | **str** | Task ID this user belongs to | 
**session_ids** | **List[str]** | List of session IDs for this user | 
**session_count** | **int** | Number of sessions for this user | 
**trace_ids** | **List[str]** | List of trace IDs for this user | 
**trace_count** | **int** | Number of traces for this user | 
**span_count** | **int** | Total number of spans for this user | 
**earliest_start_time** | **datetime** | Start time of earliest trace | 
**latest_end_time** | **datetime** | End time of latest trace | 

## Example

```python
from _generated.models.trace_user_metadata_response import TraceUserMetadataResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TraceUserMetadataResponse from a JSON string
trace_user_metadata_response_instance = TraceUserMetadataResponse.from_json(json)
# print the JSON string representation of the object
print(TraceUserMetadataResponse.to_json())

# convert the object into a dict
trace_user_metadata_response_dict = trace_user_metadata_response_instance.to_dict()
# create an instance of TraceUserMetadataResponse from a dict
trace_user_metadata_response_from_dict = TraceUserMetadataResponse.from_dict(trace_user_metadata_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


