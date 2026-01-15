# DatasetResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | ID of the dataset. | 
**task_id** | **str** | ID of the task the dataset belongs to. | 
**name** | **str** | Name of the dataset. | 
**description** | **str** |  | [optional] 
**metadata** | **object** |  | [optional] 
**created_at** | **int** | Timestamp representing the time of dataset creation in unix milliseconds. | 
**updated_at** | **int** | Timestamp representing the time of the last dataset update in unix milliseconds. | 
**latest_version_number** | **int** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.dataset_response import DatasetResponse

# TODO update the JSON string below
json = "{}"
# create an instance of DatasetResponse from a JSON string
dataset_response_instance = DatasetResponse.from_json(json)
# print the JSON string representation of the object
print(DatasetResponse.to_json())

# convert the object into a dict
dataset_response_dict = dataset_response_instance.to_dict()
# create an instance of DatasetResponse from a dict
dataset_response_from_dict = DatasetResponse.from_dict(dataset_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


