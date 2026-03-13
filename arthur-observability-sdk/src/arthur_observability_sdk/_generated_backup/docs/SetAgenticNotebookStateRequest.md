# SetAgenticNotebookStateRequest

Request to set the agentic notebook state

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**state** | [**AgenticNotebookState**](AgenticNotebookState.md) | New state for the notebook | 

## Example

```python
from _generated.models.set_agentic_notebook_state_request import SetAgenticNotebookStateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of SetAgenticNotebookStateRequest from a JSON string
set_agentic_notebook_state_request_instance = SetAgenticNotebookStateRequest.from_json(json)
# print the JSON string representation of the object
print(SetAgenticNotebookStateRequest.to_json())

# convert the object into a dict
set_agentic_notebook_state_request_dict = set_agentic_notebook_state_request_instance.to_dict()
# create an instance of SetAgenticNotebookStateRequest from a dict
set_agentic_notebook_state_request_from_dict = SetAgenticNotebookStateRequest.from_dict(set_agentic_notebook_state_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


