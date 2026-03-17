# UnsavedRagConfigResponse

Configuration for an unsaved RAG search setting (response version)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] [default to 'unsaved']
**unsaved_id** | **str** |  | [optional] 
**rag_provider_id** | **str** | ID of the RAG provider to use for this search | 
**settings** | [**Settings3**](Settings3.md) |  | 
**query_column** | [**DatasetColumnVariableSource**](DatasetColumnVariableSource.md) | Dataset column to use as the RAG search query | 

## Example

```python
from arthur_observability_sdk._generated.models.unsaved_rag_config_response import UnsavedRagConfigResponse

# TODO update the JSON string below
json = "{}"
# create an instance of UnsavedRagConfigResponse from a JSON string
unsaved_rag_config_response_instance = UnsavedRagConfigResponse.from_json(json)
# print the JSON string representation of the object
print(UnsavedRagConfigResponse.to_json())

# convert the object into a dict
unsaved_rag_config_response_dict = unsaved_rag_config_response_instance.to_dict()
# create an instance of UnsavedRagConfigResponse from a dict
unsaved_rag_config_response_from_dict = UnsavedRagConfigResponse.from_dict(unsaved_rag_config_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


