# NewDatasetRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the dataset. | 
**description** | **str** |  | [optional] 
**metadata** | **object** |  | [optional] 

## Example

```python
from _generated.models.new_dataset_request import NewDatasetRequest

# TODO update the JSON string below
json = "{}"
# create an instance of NewDatasetRequest from a JSON string
new_dataset_request_instance = NewDatasetRequest.from_json(json)
# print the JSON string representation of the object
print(NewDatasetRequest.to_json())

# convert the object into a dict
new_dataset_request_dict = new_dataset_request_instance.to_dict()
# create an instance of NewDatasetRequest from a dict
new_dataset_request_from_dict = NewDatasetRequest.from_dict(new_dataset_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


