# EvalExecutionResult

Results from an eval execution

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**score** | **float** | Score from the evaluation | 
**explanation** | **str** | Explanation of the score | 
**cost** | **str** | Cost of the evaluation | 

## Example

```python
from arthur_observability_sdk._generated.models.eval_execution_result import EvalExecutionResult

# TODO update the JSON string below
json = "{}"
# create an instance of EvalExecutionResult from a JSON string
eval_execution_result_instance = EvalExecutionResult.from_json(json)
# print the JSON string representation of the object
print(EvalExecutionResult.to_json())

# convert the object into a dict
eval_execution_result_dict = eval_execution_result_instance.to_dict()
# create an instance of EvalExecutionResult from a dict
eval_execution_result_from_dict = EvalExecutionResult.from_dict(eval_execution_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


