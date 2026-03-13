# RagConfigResultListResponse

Paginated list of results for a specific RAG configuration

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**page** | **int** | Current page number (0-indexed) | 
**page_size** | **int** | Number of items per page | 
**total_pages** | **int** | Total number of pages | 
**total_count** | **int** | Total number of records | 
**data** | [**List[RagConfigResult]**](RagConfigResult.md) | List of results for the RAG configuration | 

## Example

```python
from arthur_observability_sdk._generated.models.rag_config_result_list_response import RagConfigResultListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RagConfigResultListResponse from a JSON string
rag_config_result_list_response_instance = RagConfigResultListResponse.from_json(json)
# print the JSON string representation of the object
print(RagConfigResultListResponse.to_json())

# convert the object into a dict
rag_config_result_list_response_dict = rag_config_result_list_response_instance.to_dict()
# create an instance of RagConfigResultListResponse from a dict
rag_config_result_list_response_from_dict = RagConfigResultListResponse.from_dict(rag_config_result_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


