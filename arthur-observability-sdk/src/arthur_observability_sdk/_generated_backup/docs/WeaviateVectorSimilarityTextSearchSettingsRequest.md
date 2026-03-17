# WeaviateVectorSimilarityTextSearchSettingsRequest


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
**certainty** | **float** |  | [optional] 
**distance** | **float** |  | [optional] 
**target_vector** | [**TargetVector1**](TargetVector1.md) |  | [optional] 
**query** | [**Query**](Query.md) |  | 

## Example

```python
from _generated.models.weaviate_vector_similarity_text_search_settings_request import WeaviateVectorSimilarityTextSearchSettingsRequest

# TODO update the JSON string below
json = "{}"
# create an instance of WeaviateVectorSimilarityTextSearchSettingsRequest from a JSON string
weaviate_vector_similarity_text_search_settings_request_instance = WeaviateVectorSimilarityTextSearchSettingsRequest.from_json(json)
# print the JSON string representation of the object
print(WeaviateVectorSimilarityTextSearchSettingsRequest.to_json())

# convert the object into a dict
weaviate_vector_similarity_text_search_settings_request_dict = weaviate_vector_similarity_text_search_settings_request_instance.to_dict()
# create an instance of WeaviateVectorSimilarityTextSearchSettingsRequest from a dict
weaviate_vector_similarity_text_search_settings_request_from_dict = WeaviateVectorSimilarityTextSearchSettingsRequest.from_dict(weaviate_vector_similarity_text_search_settings_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


