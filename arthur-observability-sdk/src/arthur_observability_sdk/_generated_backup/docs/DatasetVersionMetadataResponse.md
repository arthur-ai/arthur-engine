# DatasetVersionMetadataResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version_number** | **int** | Version number of the dataset version. | 
**created_at** | **int** | Timestamp representing the time of dataset version creation in unix milliseconds. | 
**dataset_id** | **str** | ID of the dataset. | 
**column_names** | **List[str]** | Names of all columns in the dataset version. | 

## Example

```python
from _generated.models.dataset_version_metadata_response import DatasetVersionMetadataResponse

# TODO update the JSON string below
json = "{}"
# create an instance of DatasetVersionMetadataResponse from a JSON string
dataset_version_metadata_response_instance = DatasetVersionMetadataResponse.from_json(json)
# print the JSON string representation of the object
print(DatasetVersionMetadataResponse.to_json())

# convert the object into a dict
dataset_version_metadata_response_dict = dataset_version_metadata_response_instance.to_dict()
# create an instance of DatasetVersionMetadataResponse from a dict
dataset_version_metadata_response_from_dict = DatasetVersionMetadataResponse.from_dict(dataset_version_metadata_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


