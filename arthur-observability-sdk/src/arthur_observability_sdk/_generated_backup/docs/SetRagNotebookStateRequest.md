# SetRagNotebookStateRequest

Request to set the RAG notebook state

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**state** | [**RagNotebookState**](RagNotebookState.md) | New state for the notebook | 

## Example

```python
from _generated.models.set_rag_notebook_state_request import SetRagNotebookStateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of SetRagNotebookStateRequest from a JSON string
set_rag_notebook_state_request_instance = SetRagNotebookStateRequest.from_json(json)
# print the JSON string representation of the object
print(SetRagNotebookStateRequest.to_json())

# convert the object into a dict
set_rag_notebook_state_request_dict = set_rag_notebook_state_request_instance.to_dict()
# create an instance of SetRagNotebookStateRequest from a dict
set_rag_notebook_state_request_from_dict = SetRagNotebookStateRequest.from_dict(set_rag_notebook_state_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


