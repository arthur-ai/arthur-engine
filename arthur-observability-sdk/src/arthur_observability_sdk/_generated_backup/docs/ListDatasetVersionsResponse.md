# ListDatasetVersionsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**versions** | [**List[DatasetVersionMetadataResponse]**](DatasetVersionMetadataResponse.md) | List of existing versions for the dataset. | 
**page** | **int** | The current page number for the included rows. | 
**page_size** | **int** | The number of rows per page. | 
**total_pages** | **int** | The total number of pages. | 
**total_count** | **int** | The total number of rows in the dataset version. | 

## Example

```python
from _generated.models.list_dataset_versions_response import ListDatasetVersionsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ListDatasetVersionsResponse from a JSON string
list_dataset_versions_response_instance = ListDatasetVersionsResponse.from_json(json)
# print the JSON string representation of the object
print(ListDatasetVersionsResponse.to_json())

# convert the object into a dict
list_dataset_versions_response_dict = list_dataset_versions_response_instance.to_dict()
# create an instance of ListDatasetVersionsResponse from a dict
list_dataset_versions_response_from_dict = ListDatasetVersionsResponse.from_dict(list_dataset_versions_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


