# EvalVariableMappingOutput

Mapping of an eval variable to its source (dataset column or experiment output)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variable_name** | **str** | Name of the eval variable | 
**source** | [**Source1**](Source1.md) |  | 

## Example

```python
from arthur_observability_sdk._generated.models.eval_variable_mapping_output import EvalVariableMappingOutput

# TODO update the JSON string below
json = "{}"
# create an instance of EvalVariableMappingOutput from a JSON string
eval_variable_mapping_output_instance = EvalVariableMappingOutput.from_json(json)
# print the JSON string representation of the object
print(EvalVariableMappingOutput.to_json())

# convert the object into a dict
eval_variable_mapping_output_dict = eval_variable_mapping_output_instance.to_dict()
# create an instance of EvalVariableMappingOutput from a dict
eval_variable_mapping_output_from_dict = EvalVariableMappingOutput.from_dict(eval_variable_mapping_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


