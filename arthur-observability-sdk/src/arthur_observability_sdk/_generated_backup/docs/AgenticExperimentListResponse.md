# AgenticExperimentListResponse

Paginated list of agentic experiments

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**page** | **int** | Current page number (0-indexed) | 
**page_size** | **int** | Number of items per page | 
**total_pages** | **int** | Total number of pages | 
**total_count** | **int** | Total number of records | 
**data** | [**List[AgenticExperimentSummary]**](AgenticExperimentSummary.md) | List of agentic experiment summaries | 

## Example

```python
from _generated.models.agentic_experiment_list_response import AgenticExperimentListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticExperimentListResponse from a JSON string
agentic_experiment_list_response_instance = AgenticExperimentListResponse.from_json(json)
# print the JSON string representation of the object
print(AgenticExperimentListResponse.to_json())

# convert the object into a dict
agentic_experiment_list_response_dict = agentic_experiment_list_response_instance.to_dict()
# create an instance of AgenticExperimentListResponse from a dict
agentic_experiment_list_response_from_dict = AgenticExperimentListResponse.from_dict(agentic_experiment_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


