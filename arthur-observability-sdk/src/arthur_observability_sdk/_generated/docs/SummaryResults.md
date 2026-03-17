# SummaryResults

Summary results across all prompt versions and evaluations

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**prompt_eval_summaries** | [**List[PromptEvalResultSummaries]**](PromptEvalResultSummaries.md) | Summary for each prompt version tested | 

## Example

```python
from arthur_observability_sdk._generated.models.summary_results import SummaryResults

# TODO update the JSON string below
json = "{}"
# create an instance of SummaryResults from a JSON string
summary_results_instance = SummaryResults.from_json(json)
# print the JSON string representation of the object
print(SummaryResults.to_json())

# convert the object into a dict
summary_results_dict = summary_results_instance.to_dict()
# create an instance of SummaryResults from a dict
summary_results_from_dict = SummaryResults.from_dict(summary_results_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


