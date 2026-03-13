# UnsavedRagConfig

Configuration for an unsaved RAG search setting

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] [default to 'unsaved']
**unsaved_id** | **str** |  | [optional] 
**rag_provider_id** | **str** | ID of the RAG provider to use for this search | 
**settings** | [**Settings2**](Settings2.md) |  | 
**query_column** | [**DatasetColumnVariableSource**](DatasetColumnVariableSource.md) | Dataset column to use as the RAG search query | 

## Example

```python
from arthur_observability_sdk._generated.models.unsaved_rag_config import UnsavedRagConfig

# TODO update the JSON string below
json = "{}"
# create an instance of UnsavedRagConfig from a JSON string
unsaved_rag_config_instance = UnsavedRagConfig.from_json(json)
# print the JSON string representation of the object
print(UnsavedRagConfig.to_json())

# convert the object into a dict
unsaved_rag_config_dict = unsaved_rag_config_instance.to_dict()
# create an instance of UnsavedRagConfig from a dict
unsaved_rag_config_from_dict = UnsavedRagConfig.from_dict(unsaved_rag_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


