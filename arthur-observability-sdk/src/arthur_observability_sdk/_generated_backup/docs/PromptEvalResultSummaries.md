# PromptEvalResultSummaries

Summary of evaluation results for a prompt version

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**prompt_key** | **str** |  | [optional] 
**prompt_type** | **str** |  | [optional] 
**prompt_name** | **str** |  | [optional] 
**prompt_version** | **str** |  | [optional] 
**eval_results** | [**List[EvalResultSummary]**](EvalResultSummary.md) | Results for each evaluation run on this prompt version | 

## Example

```python
from _generated.models.prompt_eval_result_summaries import PromptEvalResultSummaries

# TODO update the JSON string below
json = "{}"
# create an instance of PromptEvalResultSummaries from a JSON string
prompt_eval_result_summaries_instance = PromptEvalResultSummaries.from_json(json)
# print the JSON string representation of the object
print(PromptEvalResultSummaries.to_json())

# convert the object into a dict
prompt_eval_result_summaries_dict = prompt_eval_result_summaries_instance.to_dict()
# create an instance of PromptEvalResultSummaries from a dict
prompt_eval_result_summaries_from_dict = PromptEvalResultSummaries.from_dict(prompt_eval_result_summaries_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


