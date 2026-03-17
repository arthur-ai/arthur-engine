# TraceTransformDefinition


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variables** | [**List[TraceTransformVariableDefinition]**](TraceTransformVariableDefinition.md) | List of variable extraction rules. | 

## Example

```python
from arthur_observability_sdk._generated.models.trace_transform_definition import TraceTransformDefinition

# TODO update the JSON string below
json = "{}"
# create an instance of TraceTransformDefinition from a JSON string
trace_transform_definition_instance = TraceTransformDefinition.from_json(json)
# print the JSON string representation of the object
print(TraceTransformDefinition.to_json())

# convert the object into a dict
trace_transform_definition_dict = trace_transform_definition_instance.to_dict()
# create an instance of TraceTransformDefinition from a dict
trace_transform_definition_from_dict = TraceTransformDefinition.from_dict(trace_transform_definition_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


