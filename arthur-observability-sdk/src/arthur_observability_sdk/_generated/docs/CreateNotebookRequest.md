# CreateNotebookRequest

Request to create a new notebook

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the notebook | 
**description** | **str** |  | [optional] 
**state** | [**NotebookStateInput**](NotebookStateInput.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.create_notebook_request import CreateNotebookRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreateNotebookRequest from a JSON string
create_notebook_request_instance = CreateNotebookRequest.from_json(json)
# print the JSON string representation of the object
print(CreateNotebookRequest.to_json())

# convert the object into a dict
create_notebook_request_dict = create_notebook_request_instance.to_dict()
# create an instance of CreateNotebookRequest from a dict
create_notebook_request_from_dict = CreateNotebookRequest.from_dict(create_notebook_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


