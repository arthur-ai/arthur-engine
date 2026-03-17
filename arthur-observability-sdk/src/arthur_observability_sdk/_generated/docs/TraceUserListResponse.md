# TraceUserListResponse

Response for trace user list endpoint

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | Total number of users matching filters | 
**users** | [**List[TraceUserMetadataResponse]**](TraceUserMetadataResponse.md) | List of user metadata | 

## Example

```python
from arthur_observability_sdk._generated.models.trace_user_list_response import TraceUserListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TraceUserListResponse from a JSON string
trace_user_list_response_instance = TraceUserListResponse.from_json(json)
# print the JSON string representation of the object
print(TraceUserListResponse.to_json())

# convert the object into a dict
trace_user_list_response_dict = trace_user_list_response_instance.to_dict()
# create an instance of TraceUserListResponse from a dict
trace_user_list_response_from_dict = TraceUserListResponse.from_dict(trace_user_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


