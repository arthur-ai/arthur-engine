# AgenticEvalResultSummaries

Summary of evaluation results for an agentic experiment

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**eval_name** | **str** | Name of the evaluation | 
**eval_version** | **str** | Version of the evaluation | 
**transform_id** | **str** | ID of the transform used for this evaluation | 
**eval_results** | [**List[EvalResultSummary]**](EvalResultSummary.md) | Results for this evaluation | 

## Example

```python
from _generated.models.agentic_eval_result_summaries import AgenticEvalResultSummaries

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticEvalResultSummaries from a JSON string
agentic_eval_result_summaries_instance = AgenticEvalResultSummaries.from_json(json)
# print the JSON string representation of the object
print(AgenticEvalResultSummaries.to_json())

# convert the object into a dict
agentic_eval_result_summaries_dict = agentic_eval_result_summaries_instance.to_dict()
# create an instance of AgenticEvalResultSummaries from a dict
agentic_eval_result_summaries_from_dict = AgenticEvalResultSummaries.from_dict(agentic_eval_result_summaries_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


