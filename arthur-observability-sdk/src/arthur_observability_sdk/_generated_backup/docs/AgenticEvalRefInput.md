# AgenticEvalRefInput

Reference to an evaluation configuration with transform

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the evaluation | 
**version** | **int** | Version of the evaluation | 
**variable_mapping** | [**List[AgenticEvalVariableMappingInput]**](AgenticEvalVariableMappingInput.md) | Mapping of eval variables to data sources (supports transform variables for agentic experiments) | 
**transform_id** | **str** | ID of the transform to apply to the trace before evaluation | 

## Example

```python
from _generated.models.agentic_eval_ref_input import AgenticEvalRefInput

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticEvalRefInput from a JSON string
agentic_eval_ref_input_instance = AgenticEvalRefInput.from_json(json)
# print the JSON string representation of the object
print(AgenticEvalRefInput.to_json())

# convert the object into a dict
agentic_eval_ref_input_dict = agentic_eval_ref_input_instance.to_dict()
# create an instance of AgenticEvalRefInput from a dict
agentic_eval_ref_input_from_dict = AgenticEvalRefInput.from_dict(agentic_eval_ref_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


