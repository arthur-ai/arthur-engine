# NewDatasetVersionRowRequest

Represents a row to be added to a dataset version.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**data** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) | List of column-value pairs in the new dataset row. | 

## Example

```python
from _generated.models.new_dataset_version_row_request import NewDatasetVersionRowRequest

# TODO update the JSON string below
json = "{}"
# create an instance of NewDatasetVersionRowRequest from a JSON string
new_dataset_version_row_request_instance = NewDatasetVersionRowRequest.from_json(json)
# print the JSON string representation of the object
print(NewDatasetVersionRowRequest.to_json())

# convert the object into a dict
new_dataset_version_row_request_dict = new_dataset_version_row_request_instance.to_dict()
# create an instance of NewDatasetVersionRowRequest from a dict
new_dataset_version_row_request_from_dict = NewDatasetVersionRowRequest.from_dict(new_dataset_version_row_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


