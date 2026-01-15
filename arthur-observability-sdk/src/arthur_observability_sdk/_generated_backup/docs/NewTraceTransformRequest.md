# NewTraceTransformRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the transform. | 
**description** | **str** |  | [optional] 
**definition** | [**TraceTransformDefinition**](TraceTransformDefinition.md) | Transform definition specifying extraction rules. | 

## Example

```python
from _generated.models.new_trace_transform_request import NewTraceTransformRequest

# TODO update the JSON string below
json = "{}"
# create an instance of NewTraceTransformRequest from a JSON string
new_trace_transform_request_instance = NewTraceTransformRequest.from_json(json)
# print the JSON string representation of the object
print(NewTraceTransformRequest.to_json())

# convert the object into a dict
new_trace_transform_request_dict = new_trace_transform_request_instance.to_dict()
# create an instance of NewTraceTransformRequest from a dict
new_trace_transform_request_from_dict = NewTraceTransformRequest.from_dict(new_trace_transform_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


