# RagKeywordSearchSettingRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**settings** | [**WeaviateKeywordSearchSettingsRequest**](WeaviateKeywordSearchSettingsRequest.md) | Settings for the keyword search request to the vector database. | 

## Example

```python
from _generated.models.rag_keyword_search_setting_request import RagKeywordSearchSettingRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RagKeywordSearchSettingRequest from a JSON string
rag_keyword_search_setting_request_instance = RagKeywordSearchSettingRequest.from_json(json)
# print the JSON string representation of the object
print(RagKeywordSearchSettingRequest.to_json())

# convert the object into a dict
rag_keyword_search_setting_request_dict = rag_keyword_search_setting_request_instance.to_dict()
# create an instance of RagKeywordSearchSettingRequest from a dict
rag_keyword_search_setting_request_from_dict = RagKeywordSearchSettingRequest.from_dict(rag_keyword_search_setting_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


