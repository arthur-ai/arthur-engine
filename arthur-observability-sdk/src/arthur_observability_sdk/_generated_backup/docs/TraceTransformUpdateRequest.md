# TraceTransformUpdateRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**description** | **str** |  | [optional] 
**definition** | [**TraceTransformDefinition**](TraceTransformDefinition.md) |  | [optional] 

## Example

```python
from _generated.models.trace_transform_update_request import TraceTransformUpdateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of TraceTransformUpdateRequest from a JSON string
trace_transform_update_request_instance = TraceTransformUpdateRequest.from_json(json)
# print the JSON string representation of the object
print(TraceTransformUpdateRequest.to_json())

# convert the object into a dict
trace_transform_update_request_dict = trace_transform_update_request_instance.to_dict()
# create an instance of TraceTransformUpdateRequest from a dict
trace_transform_update_request_from_dict = TraceTransformUpdateRequest.from_dict(trace_transform_update_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


