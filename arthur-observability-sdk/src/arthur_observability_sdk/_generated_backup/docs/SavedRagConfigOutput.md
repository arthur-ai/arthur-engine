# SavedRagConfigOutput

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
from _generated.models.saved_rag_config_output import SavedRagConfigOutput

# TODO update the JSON string below
json = "{}"
# create an instance of SavedRagConfigOutput from a JSON string
saved_rag_config_output_instance = SavedRagConfigOutput.from_json(json)
# print the JSON string representation of the object
print(SavedRagConfigOutput.to_json())

# convert the object into a dict
saved_rag_config_output_dict = saved_rag_config_output_instance.to_dict()
# create an instance of SavedRagConfigOutput from a dict
saved_rag_config_output_from_dict = SavedRagConfigOutput.from_dict(saved_rag_config_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


