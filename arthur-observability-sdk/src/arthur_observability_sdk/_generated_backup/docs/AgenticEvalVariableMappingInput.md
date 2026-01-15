# AgenticEvalVariableMappingInput

Mapping of an eval variable to its source (dataset column or experiment output).  For transform variables, use ExperimentOutputVariableSource with transform_variable_name in the experiment_output field. The transform_id comes from the associated AgenticEvalRef.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variable_name** | **str** | Name of the eval variable | 
**source** | [**Source**](Source.md) |  | 

## Example

```python
from _generated.models.agentic_eval_variable_mapping_input import AgenticEvalVariableMappingInput

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticEvalVariableMappingInput from a JSON string
agentic_eval_variable_mapping_input_instance = AgenticEvalVariableMappingInput.from_json(json)
# print the JSON string representation of the object
print(AgenticEvalVariableMappingInput.to_json())

# convert the object into a dict
agentic_eval_variable_mapping_input_dict = agentic_eval_variable_mapping_input_instance.to_dict()
# create an instance of AgenticEvalVariableMappingInput from a dict
agentic_eval_variable_mapping_input_from_dict = AgenticEvalVariableMappingInput.from_dict(agentic_eval_variable_mapping_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


