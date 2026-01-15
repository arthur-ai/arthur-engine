# CreateRagNotebookRequest

Request to create a new RAG notebook

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the notebook | 
**description** | **str** |  | [optional] 
**state** | [**RagNotebookState**](RagNotebookState.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.create_rag_notebook_request import CreateRagNotebookRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreateRagNotebookRequest from a JSON string
create_rag_notebook_request_instance = CreateRagNotebookRequest.from_json(json)
# print the JSON string representation of the object
print(CreateRagNotebookRequest.to_json())

# convert the object into a dict
create_rag_notebook_request_dict = create_rag_notebook_request_instance.to_dict()
# create an instance of CreateRagNotebookRequest from a dict
create_rag_notebook_request_from_dict = CreateRagNotebookRequest.from_dict(create_rag_notebook_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


