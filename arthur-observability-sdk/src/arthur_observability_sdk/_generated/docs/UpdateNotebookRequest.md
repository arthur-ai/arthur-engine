# UpdateNotebookRequest

Request to update a notebook

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**description** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.update_notebook_request import UpdateNotebookRequest

# TODO update the JSON string below
json = "{}"
# create an instance of UpdateNotebookRequest from a JSON string
update_notebook_request_instance = UpdateNotebookRequest.from_json(json)
# print the JSON string representation of the object
print(UpdateNotebookRequest.to_json())

# convert the object into a dict
update_notebook_request_dict = update_notebook_request_instance.to_dict()
# create an instance of UpdateNotebookRequest from a dict
update_notebook_request_from_dict = UpdateNotebookRequest.from_dict(update_notebook_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


