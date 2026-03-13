# WeaviateKeywordSearchSettingsRequest


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
**query** | **str** | Input text to find objects with keyword matches. | 

## Example

```python
from arthur_observability_sdk._generated.models.weaviate_keyword_search_settings_request import WeaviateKeywordSearchSettingsRequest

# TODO update the JSON string below
json = "{}"
# create an instance of WeaviateKeywordSearchSettingsRequest from a JSON string
weaviate_keyword_search_settings_request_instance = WeaviateKeywordSearchSettingsRequest.from_json(json)
# print the JSON string representation of the object
print(WeaviateKeywordSearchSettingsRequest.to_json())

# convert the object into a dict
weaviate_keyword_search_settings_request_dict = weaviate_keyword_search_settings_request_instance.to_dict()
# create an instance of WeaviateKeywordSearchSettingsRequest from a dict
weaviate_keyword_search_settings_request_from_dict = WeaviateKeywordSearchSettingsRequest.from_dict(weaviate_keyword_search_settings_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


