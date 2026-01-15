# EvalRefOutput

Reference to an evaluation configuration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the evaluation | 
**version** | **int** | Version of the evaluation | 
**variable_mapping** | [**List[EvalVariableMappingOutput]**](EvalVariableMappingOutput.md) | Mapping of eval variables to data sources | 

## Example

```python
from _generated.models.eval_ref_output import EvalRefOutput

# TODO update the JSON string below
json = "{}"
# create an instance of EvalRefOutput from a JSON string
eval_ref_output_instance = EvalRefOutput.from_json(json)
# print the JSON string representation of the object
print(EvalRefOutput.to_json())

# convert the object into a dict
eval_ref_output_dict = eval_ref_output_instance.to_dict()
# create an instance of EvalRefOutput from a dict
eval_ref_output_from_dict = EvalRefOutput.from_dict(eval_ref_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


