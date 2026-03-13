# SessionListResponse

Response for session list endpoint

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | Total number of sessions matching filters | 
**sessions** | [**List[SessionMetadataResponse]**](SessionMetadataResponse.md) | List of session metadata | 

## Example

```python
from arthur_observability_sdk._generated.models.session_list_response import SessionListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SessionListResponse from a JSON string
session_list_response_instance = SessionListResponse.from_json(json)
# print the JSON string representation of the object
print(SessionListResponse.to_json())

# convert the object into a dict
session_list_response_dict = session_list_response_instance.to_dict()
# create an instance of SessionListResponse from a dict
session_list_response_from_dict = SessionListResponse.from_dict(session_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


