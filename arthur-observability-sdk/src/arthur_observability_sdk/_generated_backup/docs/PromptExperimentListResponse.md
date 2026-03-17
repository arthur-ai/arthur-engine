# PromptExperimentListResponse

Paginated list of prompt experiments

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**page** | **int** | Current page number (0-indexed) | 
**page_size** | **int** | Number of items per page | 
**total_pages** | **int** | Total number of pages | 
**total_count** | **int** | Total number of records | 
**data** | [**List[PromptExperimentSummary]**](PromptExperimentSummary.md) | List of prompt experiment summaries | 

## Example

```python
from _generated.models.prompt_experiment_list_response import PromptExperimentListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of PromptExperimentListResponse from a JSON string
prompt_experiment_list_response_instance = PromptExperimentListResponse.from_json(json)
# print the JSON string representation of the object
print(PromptExperimentListResponse.to_json())

# convert the object into a dict
prompt_experiment_list_response_dict = prompt_experiment_list_response_instance.to_dict()
# create an instance of PromptExperimentListResponse from a dict
prompt_experiment_list_response_from_dict = PromptExperimentListResponse.from_dict(prompt_experiment_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


