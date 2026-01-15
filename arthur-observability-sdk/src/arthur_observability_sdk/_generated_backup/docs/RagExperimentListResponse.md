# RagExperimentListResponse

Paginated list of RAG experiments

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**page** | **int** | Current page number (0-indexed) | 
**page_size** | **int** | Number of items per page | 
**total_pages** | **int** | Total number of pages | 
**total_count** | **int** | Total number of records | 
**data** | [**List[RagExperimentSummary]**](RagExperimentSummary.md) | List of RAG experiment summaries | 

## Example

```python
from _generated.models.rag_experiment_list_response import RagExperimentListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RagExperimentListResponse from a JSON string
rag_experiment_list_response_instance = RagExperimentListResponse.from_json(json)
# print the JSON string representation of the object
print(RagExperimentListResponse.to_json())

# convert the object into a dict
rag_experiment_list_response_dict = rag_experiment_list_response_instance.to_dict()
# create an instance of RagExperimentListResponse from a dict
rag_experiment_list_response_from_dict = RagExperimentListResponse.from_dict(rag_experiment_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


