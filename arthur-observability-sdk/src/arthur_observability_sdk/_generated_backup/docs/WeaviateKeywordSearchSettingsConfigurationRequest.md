# WeaviateKeywordSearchSettingsConfigurationRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**collection_name** | **str** | Name of the vector collection used for the search. | 
**limit** | **int** |  | [optional] 
**include_vector** | [**IncludeVector**](IncludeVector.md) |  | [optional] 
**offset** | **int** |  | [optional] 
**auto_limit** | **int** |  | [optional] 
**return_metadata** | [**ReturnMetadata**](ReturnMetadata.md) |  | [optional] 
**return_properties** | **List[str]** |  | [optional] 
**rag_provider** | **str** |  | [optional] [default to 'weaviate']
**minimum_match_or_operator** | **int** |  | [optional] 
**and_operator** | **bool** |  | [optional] 
**search_kind** | **str** |  | [optional] [default to 'keyword_search']

## Example

```python
from _generated.models.weaviate_keyword_search_settings_configuration_request import WeaviateKeywordSearchSettingsConfigurationRequest

# TODO update the JSON string below
json = "{}"
# create an instance of WeaviateKeywordSearchSettingsConfigurationRequest from a JSON string
weaviate_keyword_search_settings_configuration_request_instance = WeaviateKeywordSearchSettingsConfigurationRequest.from_json(json)
# print the JSON string representation of the object
print(WeaviateKeywordSearchSettingsConfigurationRequest.to_json())

# convert the object into a dict
weaviate_keyword_search_settings_configuration_request_dict = weaviate_keyword_search_settings_configuration_request_instance.to_dict()
# create an instance of WeaviateKeywordSearchSettingsConfigurationRequest from a dict
weaviate_keyword_search_settings_configuration_request_from_dict = WeaviateKeywordSearchSettingsConfigurationRequest.from_dict(weaviate_keyword_search_settings_configuration_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


