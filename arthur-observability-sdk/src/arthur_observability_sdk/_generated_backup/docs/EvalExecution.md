# EvalExecution

Details of an eval execution

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**eval_name** | **str** | Name of the evaluation | 
**eval_version** | **str** | Version of the evaluation | 
**eval_input_variables** | [**List[InputVariable]**](InputVariable.md) | Input variables used for the eval | 
**eval_results** | [**EvalExecutionResult**](EvalExecutionResult.md) |  | [optional] 

## Example

```python
from _generated.models.eval_execution import EvalExecution

# TODO update the JSON string below
json = "{}"
# create an instance of EvalExecution from a JSON string
eval_execution_instance = EvalExecution.from_json(json)
# print the JSON string representation of the object
print(EvalExecution.to_json())

# convert the object into a dict
eval_execution_dict = eval_execution_instance.to_dict()
# create an instance of EvalExecution from a dict
eval_execution_from_dict = EvalExecution.from_dict(eval_execution_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


