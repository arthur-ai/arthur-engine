# AgenticEvalRefOutput

Reference to an evaluation configuration with transform

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the evaluation | 
**version** | **int** | Version of the evaluation | 
**variable_mapping** | [**List[AgenticEvalVariableMappingOutput]**](AgenticEvalVariableMappingOutput.md) | Mapping of eval variables to data sources (supports transform variables for agentic experiments) | 
**transform_id** | **str** | ID of the transform to apply to the trace before evaluation | 

## Example

```python
from _generated.models.agentic_eval_ref_output import AgenticEvalRefOutput

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticEvalRefOutput from a JSON string
agentic_eval_ref_output_instance = AgenticEvalRefOutput.from_json(json)
# print the JSON string representation of the object
print(AgenticEvalRefOutput.to_json())

# convert the object into a dict
agentic_eval_ref_output_dict = agentic_eval_ref_output_instance.to_dict()
# create an instance of AgenticEvalRefOutput from a dict
agentic_eval_ref_output_from_dict = AgenticEvalRefOutput.from_dict(agentic_eval_ref_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


