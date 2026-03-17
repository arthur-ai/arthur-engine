# DatasetColumnVariableSource

Variable source from a dataset column

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | Type of source: &#39;dataset_column&#39; | 
**dataset_column** | [**DatasetColumnSource**](DatasetColumnSource.md) | Dataset column source | 

## Example

```python
from arthur_observability_sdk._generated.models.dataset_column_variable_source import DatasetColumnVariableSource

# TODO update the JSON string below
json = "{}"
# create an instance of DatasetColumnVariableSource from a JSON string
dataset_column_variable_source_instance = DatasetColumnVariableSource.from_json(json)
# print the JSON string representation of the object
print(DatasetColumnVariableSource.to_json())

# convert the object into a dict
dataset_column_variable_source_dict = dataset_column_variable_source_instance.to_dict()
# create an instance of DatasetColumnVariableSource from a dict
dataset_column_variable_source_from_dict = DatasetColumnVariableSource.from_dict(dataset_column_variable_source_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


