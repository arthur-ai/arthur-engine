# TraceTransformVariableDefinition


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variable_name** | **str** | Name of the variable to extract. | 
**span_name** | **str** | Name of the span to extract data from. | 
**attribute_path** | **str** | Dot-notation path to the attribute within the span (e.g., &#39;attributes.input.value.sqlQuery&#39;). | 
**fallback** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.trace_transform_variable_definition import TraceTransformVariableDefinition

# TODO update the JSON string below
json = "{}"
# create an instance of TraceTransformVariableDefinition from a JSON string
trace_transform_variable_definition_instance = TraceTransformVariableDefinition.from_json(json)
# print the JSON string representation of the object
print(TraceTransformVariableDefinition.to_json())

# convert the object into a dict
trace_transform_variable_definition_dict = trace_transform_variable_definition_instance.to_dict()
# create an instance of TraceTransformVariableDefinition from a dict
trace_transform_variable_definition_from_dict = TraceTransformVariableDefinition.from_dict(trace_transform_variable_definition_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


