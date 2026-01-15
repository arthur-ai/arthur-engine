# RagHybridSearchSettingRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**settings** | [**WeaviateHybridSearchSettingsRequest**](WeaviateHybridSearchSettingsRequest.md) | Settings for the hybrid search request to the vector database. | 

## Example

```python
from _generated.models.rag_hybrid_search_setting_request import RagHybridSearchSettingRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RagHybridSearchSettingRequest from a JSON string
rag_hybrid_search_setting_request_instance = RagHybridSearchSettingRequest.from_json(json)
# print the JSON string representation of the object
print(RagHybridSearchSettingRequest.to_json())

# convert the object into a dict
rag_hybrid_search_setting_request_dict = rag_hybrid_search_setting_request_instance.to_dict()
# create an instance of RagHybridSearchSettingRequest from a dict
rag_hybrid_search_setting_request_from_dict = RagHybridSearchSettingRequest.from_dict(rag_hybrid_search_setting_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


