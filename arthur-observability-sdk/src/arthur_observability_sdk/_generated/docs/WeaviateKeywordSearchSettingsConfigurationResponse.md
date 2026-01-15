# WeaviateKeywordSearchSettingsConfigurationResponse


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
**search_kind** | **str** |  | [optional] [default to 'keyword_search']
**minimum_match_or_operator** | **int** |  | [optional] 
**and_operator** | **bool** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.weaviate_keyword_search_settings_configuration_response import WeaviateKeywordSearchSettingsConfigurationResponse

# TODO update the JSON string below
json = "{}"
# create an instance of WeaviateKeywordSearchSettingsConfigurationResponse from a JSON string
weaviate_keyword_search_settings_configuration_response_instance = WeaviateKeywordSearchSettingsConfigurationResponse.from_json(json)
# print the JSON string representation of the object
print(WeaviateKeywordSearchSettingsConfigurationResponse.to_json())

# convert the object into a dict
weaviate_keyword_search_settings_configuration_response_dict = weaviate_keyword_search_settings_configuration_response_instance.to_dict()
# create an instance of WeaviateKeywordSearchSettingsConfigurationResponse from a dict
weaviate_keyword_search_settings_configuration_response_from_dict = WeaviateKeywordSearchSettingsConfigurationResponse.from_dict(weaviate_keyword_search_settings_configuration_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


