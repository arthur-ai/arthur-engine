# NewDatasetVersionUpdateRowRequest

Represents a row to be updated in a dataset version.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | UUID of row to be updated. | 
**data** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) | List of column-value pairs in the updated row. | 

## Example

```python
from _generated.models.new_dataset_version_update_row_request import NewDatasetVersionUpdateRowRequest

# TODO update the JSON string below
json = "{}"
# create an instance of NewDatasetVersionUpdateRowRequest from a JSON string
new_dataset_version_update_row_request_instance = NewDatasetVersionUpdateRowRequest.from_json(json)
# print the JSON string representation of the object
print(NewDatasetVersionUpdateRowRequest.to_json())

# convert the object into a dict
new_dataset_version_update_row_request_dict = new_dataset_version_update_row_request_instance.to_dict()
# create an instance of NewDatasetVersionUpdateRowRequest from a dict
new_dataset_version_update_row_request_from_dict = NewDatasetVersionUpdateRowRequest.from_dict(new_dataset_version_update_row_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


