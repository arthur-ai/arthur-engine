# UpdateRagNotebookRequest

Request to update a RAG notebook

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**description** | **str** |  | [optional] 

## Example

```python
from _generated.models.update_rag_notebook_request import UpdateRagNotebookRequest

# TODO update the JSON string below
json = "{}"
# create an instance of UpdateRagNotebookRequest from a JSON string
update_rag_notebook_request_instance = UpdateRagNotebookRequest.from_json(json)
# print the JSON string representation of the object
print(UpdateRagNotebookRequest.to_json())

# convert the object into a dict
update_rag_notebook_request_dict = update_rag_notebook_request_instance.to_dict()
# create an instance of UpdateRagNotebookRequest from a dict
update_rag_notebook_request_from_dict = UpdateRagNotebookRequest.from_dict(update_rag_notebook_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


