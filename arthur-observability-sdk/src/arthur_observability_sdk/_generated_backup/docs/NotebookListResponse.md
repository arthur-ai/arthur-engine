# NotebookListResponse

Paginated list of notebooks

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**data** | [**List[NotebookSummary]**](NotebookSummary.md) | List of notebook summaries | 
**page** | **int** | Current page number (0-indexed) | 
**page_size** | **int** | Number of items per page | 
**total_pages** | **int** | Total number of pages | 
**total_count** | **int** | Total number of notebooks | 

## Example

```python
from _generated.models.notebook_list_response import NotebookListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of NotebookListResponse from a JSON string
notebook_list_response_instance = NotebookListResponse.from_json(json)
# print the JSON string representation of the object
print(NotebookListResponse.to_json())

# convert the object into a dict
notebook_list_response_dict = notebook_list_response_instance.to_dict()
# create an instance of NotebookListResponse from a dict
notebook_list_response_from_dict = NotebookListResponse.from_dict(notebook_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


