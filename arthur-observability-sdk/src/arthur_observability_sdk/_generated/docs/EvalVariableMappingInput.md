# EvalVariableMappingInput

Mapping of an eval variable to its source (dataset column or experiment output)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variable_name** | **str** | Name of the eval variable | 
**source** | [**Source1**](Source1.md) |  | 

## Example

```python
from arthur_observability_sdk._generated.models.eval_variable_mapping_input import EvalVariableMappingInput

# TODO update the JSON string below
json = "{}"
# create an instance of EvalVariableMappingInput from a JSON string
eval_variable_mapping_input_instance = EvalVariableMappingInput.from_json(json)
# print the JSON string representation of the object
print(EvalVariableMappingInput.to_json())

# convert the object into a dict
eval_variable_mapping_input_dict = eval_variable_mapping_input_instance.to_dict()
# create an instance of EvalVariableMappingInput from a dict
eval_variable_mapping_input_from_dict = EvalVariableMappingInput.from_dict(eval_variable_mapping_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


