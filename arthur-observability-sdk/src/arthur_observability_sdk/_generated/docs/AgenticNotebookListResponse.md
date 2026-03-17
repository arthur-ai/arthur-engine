# AgenticNotebookListResponse

Paginated list of agentic notebooks

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**page** | **int** | Current page number (0-indexed) | 
**page_size** | **int** | Number of items per page | 
**total_pages** | **int** | Total number of pages | 
**total_count** | **int** | Total number of records | 
**data** | [**List[AgenticNotebookSummary]**](AgenticNotebookSummary.md) | List of notebook summaries | 

## Example

```python
from arthur_observability_sdk._generated.models.agentic_notebook_list_response import AgenticNotebookListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticNotebookListResponse from a JSON string
agentic_notebook_list_response_instance = AgenticNotebookListResponse.from_json(json)
# print the JSON string representation of the object
print(AgenticNotebookListResponse.to_json())

# convert the object into a dict
agentic_notebook_list_response_dict = agentic_notebook_list_response_instance.to_dict()
# create an instance of AgenticNotebookListResponse from a dict
agentic_notebook_list_response_from_dict = AgenticNotebookListResponse.from_dict(agentic_notebook_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


