# DatasetRefInput

Reference to a dataset and version for input (without name)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | Dataset ID | 
**version** | **int** | Dataset version number | 

## Example

```python
from _generated.models.dataset_ref_input import DatasetRefInput

# TODO update the JSON string below
json = "{}"
# create an instance of DatasetRefInput from a JSON string
dataset_ref_input_instance = DatasetRefInput.from_json(json)
# print the JSON string representation of the object
print(DatasetRefInput.to_json())

# convert the object into a dict
dataset_ref_input_dict = dataset_ref_input_instance.to_dict()
# create an instance of DatasetRefInput from a dict
dataset_ref_input_from_dict = DatasetRefInput.from_dict(dataset_ref_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


