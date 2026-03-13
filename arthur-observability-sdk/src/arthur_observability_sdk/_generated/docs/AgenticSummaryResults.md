# AgenticSummaryResults

Summary results across all evaluations

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**eval_summaries** | [**List[AgenticEvalResultSummaries]**](AgenticEvalResultSummaries.md) | Summary for each evaluation run | 

## Example

```python
from arthur_observability_sdk._generated.models.agentic_summary_results import AgenticSummaryResults

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticSummaryResults from a JSON string
agentic_summary_results_instance = AgenticSummaryResults.from_json(json)
# print the JSON string representation of the object
print(AgenticSummaryResults.to_json())

# convert the object into a dict
agentic_summary_results_dict = agentic_summary_results_instance.to_dict()
# create an instance of AgenticSummaryResults from a dict
agentic_summary_results_from_dict = AgenticSummaryResults.from_dict(agentic_summary_results_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


