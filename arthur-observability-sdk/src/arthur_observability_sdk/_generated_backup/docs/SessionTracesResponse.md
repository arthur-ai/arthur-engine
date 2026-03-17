# SessionTracesResponse

Response for session traces endpoint

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**session_id** | **str** | Session identifier | 
**count** | **int** | Number of traces in this session | 
**traces** | [**List[TraceResponse]**](TraceResponse.md) | List of full trace trees | 

## Example

```python
from _generated.models.session_traces_response import SessionTracesResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SessionTracesResponse from a JSON string
session_traces_response_instance = SessionTracesResponse.from_json(json)
# print the JSON string representation of the object
print(SessionTracesResponse.to_json())

# convert the object into a dict
session_traces_response_dict = session_traces_response_instance.to_dict()
# create an instance of SessionTracesResponse from a dict
session_traces_response_from_dict = SessionTracesResponse.from_dict(session_traces_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


