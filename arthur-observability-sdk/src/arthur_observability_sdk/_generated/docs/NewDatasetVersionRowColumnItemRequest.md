# NewDatasetVersionRowColumnItemRequest

Represents a single column-value pair in a dataset row.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**column_name** | **str** | Name of column. | 
**column_value** | **str** | Value of column for the row. | 

## Example

```python
from arthur_observability_sdk._generated.models.new_dataset_version_row_column_item_request import NewDatasetVersionRowColumnItemRequest

# TODO update the JSON string below
json = "{}"
# create an instance of NewDatasetVersionRowColumnItemRequest from a JSON string
new_dataset_version_row_column_item_request_instance = NewDatasetVersionRowColumnItemRequest.from_json(json)
# print the JSON string representation of the object
print(NewDatasetVersionRowColumnItemRequest.to_json())

# convert the object into a dict
new_dataset_version_row_column_item_request_dict = new_dataset_version_row_column_item_request_instance.to_dict()
# create an instance of NewDatasetVersionRowColumnItemRequest from a dict
new_dataset_version_row_column_item_request_from_dict = NewDatasetVersionRowColumnItemRequest.from_dict(new_dataset_version_row_column_item_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


