# DatasetRef

Reference to a dataset and version (with name)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | Dataset ID | 
**name** | **str** | Dataset name | 
**version** | **int** | Dataset version number | 

## Example

```python
from arthur_observability_sdk._generated.models.dataset_ref import DatasetRef

# TODO update the JSON string below
json = "{}"
# create an instance of DatasetRef from a JSON string
dataset_ref_instance = DatasetRef.from_json(json)
# print the JSON string representation of the object
print(DatasetRef.to_json())

# convert the object into a dict
dataset_ref_dict = dataset_ref_instance.to_dict()
# create an instance of DatasetRef from a dict
dataset_ref_from_dict = DatasetRef.from_dict(dataset_ref_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


