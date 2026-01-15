# PromptResult

Results from a prompt execution with evals

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**evals** | [**List[EvalExecution]**](EvalExecution.md) | Evaluation results for this execution | 
**prompt_key** | **str** | Prompt key: &#39;saved:name:version&#39; or &#39;unsaved:auto_name&#39; | 
**prompt_type** | **str** | Type: &#39;saved&#39; or &#39;unsaved&#39; | 
**name** | **str** |  | [optional] 
**version** | **str** |  | [optional] 
**rendered_prompt** | **str** | Prompt with variables replaced | 
**output** | [**PromptOutput**](PromptOutput.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.prompt_result import PromptResult

# TODO update the JSON string below
json = "{}"
# create an instance of PromptResult from a JSON string
prompt_result_instance = PromptResult.from_json(json)
# print the JSON string representation of the object
print(PromptResult.to_json())

# convert the object into a dict
prompt_result_dict = prompt_result_instance.to_dict()
# create an instance of PromptResult from a dict
prompt_result_from_dict = PromptResult.from_dict(prompt_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


