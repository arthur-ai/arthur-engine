# DatasetVersionRowResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | ID of the version field. | 
**data** | [**List[DatasetVersionRowColumnItemResponse]**](DatasetVersionRowColumnItemResponse.md) | List of column names and values in the row. | 
**created_at** | **int** | Timestamp representing the time of dataset row creation in unix milliseconds. May differ within a version if a row already existed in a past version of the dataset. | 

## Example

```python
from arthur_observability_sdk._generated.models.dataset_version_row_response import DatasetVersionRowResponse

# TODO update the JSON string below
json = "{}"
# create an instance of DatasetVersionRowResponse from a JSON string
dataset_version_row_response_instance = DatasetVersionRowResponse.from_json(json)
# print the JSON string representation of the object
print(DatasetVersionRowResponse.to_json())

# convert the object into a dict
dataset_version_row_response_dict = dataset_version_row_response_instance.to_dict()
# create an instance of DatasetVersionRowResponse from a dict
dataset_version_row_response_from_dict = DatasetVersionRowResponse.from_dict(dataset_version_row_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


