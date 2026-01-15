# CreateAgenticNotebookRequest

Request to create a new agentic notebook

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the notebook | 
**description** | **str** |  | [optional] 
**state** | [**AgenticNotebookState**](AgenticNotebookState.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.create_agentic_notebook_request import CreateAgenticNotebookRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreateAgenticNotebookRequest from a JSON string
create_agentic_notebook_request_instance = CreateAgenticNotebookRequest.from_json(json)
# print the JSON string representation of the object
print(CreateAgenticNotebookRequest.to_json())

# convert the object into a dict
create_agentic_notebook_request_dict = create_agentic_notebook_request_instance.to_dict()
# create an instance of CreateAgenticNotebookRequest from a dict
create_agentic_notebook_request_from_dict = CreateAgenticNotebookRequest.from_dict(create_agentic_notebook_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


