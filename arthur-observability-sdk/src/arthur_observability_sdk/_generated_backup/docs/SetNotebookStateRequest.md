# SetNotebookStateRequest

Request to set the notebook state

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**state** | [**NotebookStateInput**](NotebookStateInput.md) | New state for the notebook | 

## Example

```python
from _generated.models.set_notebook_state_request import SetNotebookStateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of SetNotebookStateRequest from a JSON string
set_notebook_state_request_instance = SetNotebookStateRequest.from_json(json)
# print the JSON string representation of the object
print(SetNotebookStateRequest.to_json())

# convert the object into a dict
set_notebook_state_request_dict = set_notebook_state_request_instance.to_dict()
# create an instance of SetNotebookStateRequest from a dict
set_notebook_state_request_from_dict = SetNotebookStateRequest.from_dict(set_notebook_state_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


