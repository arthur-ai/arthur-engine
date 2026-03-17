# NewDatasetVersionRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**rows_to_add** | [**List[NewDatasetVersionRowRequest]**](NewDatasetVersionRowRequest.md) | List of rows to be added to the new dataset version. | 
**rows_to_delete** | **List[str]** | List of IDs of rows to be deleted from the new dataset version. | 
**rows_to_delete_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**rows_to_update** | [**List[NewDatasetVersionUpdateRowRequest]**](NewDatasetVersionUpdateRowRequest.md) | List of IDs of rows to be updated in the new dataset version with their new values. Should include the value in the row for every column in the dataset, not just the updated column values. | 

## Example

```python
from arthur_observability_sdk._generated.models.new_dataset_version_request import NewDatasetVersionRequest

# TODO update the JSON string below
json = "{}"
# create an instance of NewDatasetVersionRequest from a JSON string
new_dataset_version_request_instance = NewDatasetVersionRequest.from_json(json)
# print the JSON string representation of the object
print(NewDatasetVersionRequest.to_json())

# convert the object into a dict
new_dataset_version_request_dict = new_dataset_version_request_instance.to_dict()
# create an instance of NewDatasetVersionRequest from a dict
new_dataset_version_request_from_dict = NewDatasetVersionRequest.from_dict(new_dataset_version_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


