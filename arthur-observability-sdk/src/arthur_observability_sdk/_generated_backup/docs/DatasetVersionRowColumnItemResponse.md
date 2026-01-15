# DatasetVersionRowColumnItemResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**column_name** | **str** | Name of the column. | 
**column_value** | **str** | Value of the column. | 

## Example

```python
from _generated.models.dataset_version_row_column_item_response import DatasetVersionRowColumnItemResponse

# TODO update the JSON string below
json = "{}"
# create an instance of DatasetVersionRowColumnItemResponse from a JSON string
dataset_version_row_column_item_response_instance = DatasetVersionRowColumnItemResponse.from_json(json)
# print the JSON string representation of the object
print(DatasetVersionRowColumnItemResponse.to_json())

# convert the object into a dict
dataset_version_row_column_item_response_dict = dataset_version_row_column_item_response_instance.to_dict()
# create an instance of DatasetVersionRowColumnItemResponse from a dict
dataset_version_row_column_item_response_from_dict = DatasetVersionRowColumnItemResponse.from_dict(dataset_version_row_column_item_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


