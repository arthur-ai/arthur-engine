# RagSummaryResults

Summary results across all RAG configurations and evaluations

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**rag_eval_summaries** | [**List[RagEvalResultSummaries]**](RagEvalResultSummaries.md) | Summary for each RAG configuration tested | 

## Example

```python
from _generated.models.rag_summary_results import RagSummaryResults

# TODO update the JSON string below
json = "{}"
# create an instance of RagSummaryResults from a JSON string
rag_summary_results_instance = RagSummaryResults.from_json(json)
# print the JSON string representation of the object
print(RagSummaryResults.to_json())

# convert the object into a dict
rag_summary_results_dict = rag_summary_results_instance.to_dict()
# create an instance of RagSummaryResults from a dict
rag_summary_results_from_dict = RagSummaryResults.from_dict(rag_summary_results_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


