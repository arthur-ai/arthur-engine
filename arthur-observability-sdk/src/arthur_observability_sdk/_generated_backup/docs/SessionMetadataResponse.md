# SessionMetadataResponse

Session summary metadata

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**prompt_token_count** | **int** |  | [optional] 
**completion_token_count** | **int** |  | [optional] 
**total_token_count** | **int** |  | [optional] 
**prompt_token_cost** | **float** |  | [optional] 
**completion_token_cost** | **float** |  | [optional] 
**total_token_cost** | **float** |  | [optional] 
**session_id** | **str** | Session identifier | 
**task_id** | **str** | Task ID this session belongs to | 
**user_id** | **str** |  | [optional] 
**trace_ids** | **List[str]** | List of trace IDs in this session | 
**trace_count** | **int** | Number of traces in this session | 
**span_count** | **int** | Total number of spans in this session | 
**earliest_start_time** | **datetime** | Start time of earliest trace | 
**latest_end_time** | **datetime** | End time of latest trace | 
**duration_ms** | **float** | Total session duration in milliseconds | 

## Example

```python
from _generated.models.session_metadata_response import SessionMetadataResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SessionMetadataResponse from a JSON string
session_metadata_response_instance = SessionMetadataResponse.from_json(json)
# print the JSON string representation of the object
print(SessionMetadataResponse.to_json())

# convert the object into a dict
session_metadata_response_dict = session_metadata_response_instance.to_dict()
# create an instance of SessionMetadataResponse from a dict
session_metadata_response_from_dict = SessionMetadataResponse.from_dict(session_metadata_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


