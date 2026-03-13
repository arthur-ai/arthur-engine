# TraceTransformResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | ID of the transform. | 
**task_id** | **str** | ID of the parent task. | 
**name** | **str** | Name of the transform. | 
**description** | **str** |  | [optional] 
**definition** | [**TraceTransformDefinition**](TraceTransformDefinition.md) | Transform definition specifying extraction rules. | 
**created_at** | **datetime** | Timestamp representing the time of transform creation | 
**updated_at** | **datetime** | Timestamp representing the time of the last transform update | 

## Example

```python
from _generated.models.trace_transform_response import TraceTransformResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TraceTransformResponse from a JSON string
trace_transform_response_instance = TraceTransformResponse.from_json(json)
# print the JSON string representation of the object
print(TraceTransformResponse.to_json())

# convert the object into a dict
trace_transform_response_dict = trace_transform_response_instance.to_dict()
# create an instance of TraceTransformResponse from a dict
trace_transform_response_from_dict = TraceTransformResponse.from_dict(trace_transform_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


