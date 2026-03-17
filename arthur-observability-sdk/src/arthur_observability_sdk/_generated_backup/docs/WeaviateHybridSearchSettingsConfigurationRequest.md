# WeaviateHybridSearchSettingsConfigurationRequest


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
**alpha** | **float** | Balance between the relative weights of the keyword and vector search. 1 is pure vector search, 0 is pure keyword search. | [optional] [default to 0.7]
**query_properties** | **List[str]** |  | [optional] 
**fusion_type** | [**HybridFusion**](HybridFusion.md) |  | [optional] 
**max_vector_distance** | **float** |  | [optional] 
**minimum_match_or_operator** | **int** |  | [optional] 
**and_operator** | **bool** |  | [optional] 
**target_vector** | [**TargetVector**](TargetVector.md) |  | [optional] 
**search_kind** | **str** |  | [optional] [default to 'hybrid_search']

## Example

```python
from _generated.models.weaviate_hybrid_search_settings_configuration_request import WeaviateHybridSearchSettingsConfigurationRequest

# TODO update the JSON string below
json = "{}"
# create an instance of WeaviateHybridSearchSettingsConfigurationRequest from a JSON string
weaviate_hybrid_search_settings_configuration_request_instance = WeaviateHybridSearchSettingsConfigurationRequest.from_json(json)
# print the JSON string representation of the object
print(WeaviateHybridSearchSettingsConfigurationRequest.to_json())

# convert the object into a dict
weaviate_hybrid_search_settings_configuration_request_dict = weaviate_hybrid_search_settings_configuration_request_instance.to_dict()
# create an instance of WeaviateHybridSearchSettingsConfigurationRequest from a dict
weaviate_hybrid_search_settings_configuration_request_from_dict = WeaviateHybridSearchSettingsConfigurationRequest.from_dict(weaviate_hybrid_search_settings_configuration_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


