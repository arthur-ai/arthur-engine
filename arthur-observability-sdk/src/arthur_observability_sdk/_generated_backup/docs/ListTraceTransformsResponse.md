# ListTraceTransformsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**transforms** | [**List[TraceTransformResponse]**](TraceTransformResponse.md) | List of transforms for the task. | 

## Example

```python
from _generated.models.list_trace_transforms_response import ListTraceTransformsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ListTraceTransformsResponse from a JSON string
list_trace_transforms_response_instance = ListTraceTransformsResponse.from_json(json)
# print the JSON string representation of the object
print(ListTraceTransformsResponse.to_json())

# convert the object into a dict
list_trace_transforms_response_dict = list_trace_transforms_response_instance.to_dict()
# create an instance of ListTraceTransformsResponse from a dict
list_trace_transforms_response_from_dict = ListTraceTransformsResponse.from_dict(list_trace_transforms_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


