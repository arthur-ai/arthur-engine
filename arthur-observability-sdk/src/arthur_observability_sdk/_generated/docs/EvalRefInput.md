# EvalRefInput

Reference to an evaluation configuration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the evaluation | 
**version** | **int** | Version of the evaluation | 
**variable_mapping** | [**List[EvalVariableMappingInput]**](EvalVariableMappingInput.md) | Mapping of eval variables to data sources | 

## Example

```python
from arthur_observability_sdk._generated.models.eval_ref_input import EvalRefInput

# TODO update the JSON string below
json = "{}"
# create an instance of EvalRefInput from a JSON string
eval_ref_input_instance = EvalRefInput.from_json(json)
# print the JSON string representation of the object
print(EvalRefInput.to_json())

# convert the object into a dict
eval_ref_input_dict = eval_ref_input_instance.to_dict()
# create an instance of EvalRefInput from a dict
eval_ref_input_from_dict = EvalRefInput.from_dict(eval_ref_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


