# RagNotebookListResponse

Paginated list of RAG notebooks

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**page** | **int** | Current page number (0-indexed) | 
**page_size** | **int** | Number of items per page | 
**total_pages** | **int** | Total number of pages | 
**total_count** | **int** | Total number of records | 
**data** | [**List[RagNotebookSummary]**](RagNotebookSummary.md) | List of notebook summaries | 

## Example

```python
from arthur_observability_sdk._generated.models.rag_notebook_list_response import RagNotebookListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RagNotebookListResponse from a JSON string
rag_notebook_list_response_instance = RagNotebookListResponse.from_json(json)
# print the JSON string representation of the object
print(RagNotebookListResponse.to_json())

# convert the object into a dict
rag_notebook_list_response_dict = rag_notebook_list_response_instance.to_dict()
# create an instance of RagNotebookListResponse from a dict
rag_notebook_list_response_from_dict = RagNotebookListResponse.from_dict(rag_notebook_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


