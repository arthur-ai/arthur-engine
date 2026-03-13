# PromptVersionResult

Result for a specific prompt version within a test case

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | [**TestCaseStatus**](TestCaseStatus.md) | Status of the test case | 
**dataset_row_id** | **str** | ID of the dataset row | 
**evals** | [**List[EvalExecution]**](EvalExecution.md) | Evaluation results for this specific config | 
**total_cost** | **str** |  | [optional] 
**prompt_input_variables** | [**List[InputVariable]**](InputVariable.md) | Input variables for the prompt | 
**rendered_prompt** | **str** | Prompt with variables replaced | 
**output** | [**PromptOutput**](PromptOutput.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.prompt_version_result import PromptVersionResult

# TODO update the JSON string below
json = "{}"
# create an instance of PromptVersionResult from a JSON string
prompt_version_result_instance = PromptVersionResult.from_json(json)
# print the JSON string representation of the object
print(PromptVersionResult.to_json())

# convert the object into a dict
prompt_version_result_dict = prompt_version_result_instance.to_dict()
# create an instance of PromptVersionResult from a dict
prompt_version_result_from_dict = PromptVersionResult.from_dict(prompt_version_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


