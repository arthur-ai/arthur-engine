# RagEvalResultSummaries

Summary of evaluation results for a RAG configuration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**rag_config_key** | **str** |  | [optional] 
**rag_config_type** | **str** |  | [optional] 
**setting_configuration_id** | **str** |  | [optional] 
**setting_configuration_version** | **int** |  | [optional] 
**eval_results** | [**List[EvalResultSummary]**](EvalResultSummary.md) | Results for each evaluation run on this RAG configuration | 

## Example

```python
from arthur_observability_sdk._generated.models.rag_eval_result_summaries import RagEvalResultSummaries

# TODO update the JSON string below
json = "{}"
# create an instance of RagEvalResultSummaries from a JSON string
rag_eval_result_summaries_instance = RagEvalResultSummaries.from_json(json)
# print the JSON string representation of the object
print(RagEvalResultSummaries.to_json())

# convert the object into a dict
rag_eval_result_summaries_dict = rag_eval_result_summaries_instance.to_dict()
# create an instance of RagEvalResultSummaries from a dict
rag_eval_result_summaries_from_dict = RagEvalResultSummaries.from_dict(rag_eval_result_summaries_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


