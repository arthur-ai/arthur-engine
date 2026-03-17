# DatasetVersionResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version_number** | **int** | Version number of the dataset version. | 
**created_at** | **int** | Timestamp representing the time of dataset version creation in unix milliseconds. | 
**dataset_id** | **str** | ID of the dataset. | 
**column_names** | **List[str]** | Names of all columns in the dataset version. | 
**rows** | [**List[DatasetVersionRowResponse]**](DatasetVersionRowResponse.md) | list of rows in the dataset version. | 
**page** | **int** | The current page number for the included rows. | 
**page_size** | **int** | The number of rows per page. | 
**total_pages** | **int** | The total number of pages. | 
**total_count** | **int** | The total number of rows in the dataset version. | 

## Example

```python
from arthur_observability_sdk._generated.models.dataset_version_response import DatasetVersionResponse

# TODO update the JSON string below
json = "{}"
# create an instance of DatasetVersionResponse from a JSON string
dataset_version_response_instance = DatasetVersionResponse.from_json(json)
# print the JSON string representation of the object
print(DatasetVersionResponse.to_json())

# convert the object into a dict
dataset_version_response_dict = dataset_version_response_instance.to_dict()
# create an instance of DatasetVersionResponse from a dict
dataset_version_response_from_dict = DatasetVersionResponse.from_dict(dataset_version_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


