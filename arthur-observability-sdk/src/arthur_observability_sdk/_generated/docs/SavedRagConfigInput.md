# SavedRagConfigInput

Configuration for a saved RAG setting configuration version

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] [default to 'saved']
**setting_configuration_id** | **str** | ID of the RAG search setting configuration | 
**version** | **int** | Version of the RAG search setting configuration | 
**query_column** | [**DatasetColumnVariableSource**](DatasetColumnVariableSource.md) | Dataset column to use as the RAG search query | 

## Example

```python
from arthur_observability_sdk._generated.models.saved_rag_config_input import SavedRagConfigInput

# TODO update the JSON string below
json = "{}"
# create an instance of SavedRagConfigInput from a JSON string
saved_rag_config_input_instance = SavedRagConfigInput.from_json(json)
# print the JSON string representation of the object
print(SavedRagConfigInput.to_json())

# convert the object into a dict
saved_rag_config_input_dict = saved_rag_config_input_instance.to_dict()
# create an instance of SavedRagConfigInput from a dict
saved_rag_config_input_from_dict = SavedRagConfigInput.from_dict(saved_rag_config_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


