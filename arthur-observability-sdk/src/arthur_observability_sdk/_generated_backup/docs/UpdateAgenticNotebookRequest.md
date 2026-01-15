# UpdateAgenticNotebookRequest

Request to update an agentic notebook

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**description** | **str** |  | [optional] 

## Example

```python
from _generated.models.update_agentic_notebook_request import UpdateAgenticNotebookRequest

# TODO update the JSON string below
json = "{}"
# create an instance of UpdateAgenticNotebookRequest from a JSON string
update_agentic_notebook_request_instance = UpdateAgenticNotebookRequest.from_json(json)
# print the JSON string representation of the object
print(UpdateAgenticNotebookRequest.to_json())

# convert the object into a dict
update_agentic_notebook_request_dict = update_agentic_notebook_request_instance.to_dict()
# create an instance of UpdateAgenticNotebookRequest from a dict
update_agentic_notebook_request_from_dict = UpdateAgenticNotebookRequest.from_dict(update_agentic_notebook_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


