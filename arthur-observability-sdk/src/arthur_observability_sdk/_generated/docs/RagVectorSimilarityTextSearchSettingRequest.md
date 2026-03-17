# RagVectorSimilarityTextSearchSettingRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**settings** | [**WeaviateVectorSimilarityTextSearchSettingsRequest**](WeaviateVectorSimilarityTextSearchSettingsRequest.md) | Settings for the similarity text search request to the vector database. | 

## Example

```python
from arthur_observability_sdk._generated.models.rag_vector_similarity_text_search_setting_request import RagVectorSimilarityTextSearchSettingRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RagVectorSimilarityTextSearchSettingRequest from a JSON string
rag_vector_similarity_text_search_setting_request_instance = RagVectorSimilarityTextSearchSettingRequest.from_json(json)
# print the JSON string representation of the object
print(RagVectorSimilarityTextSearchSettingRequest.to_json())

# convert the object into a dict
rag_vector_similarity_text_search_setting_request_dict = rag_vector_similarity_text_search_setting_request_instance.to_dict()
# create an instance of RagVectorSimilarityTextSearchSettingRequest from a dict
rag_vector_similarity_text_search_setting_request_from_dict = RagVectorSimilarityTextSearchSettingRequest.from_dict(rag_vector_similarity_text_search_setting_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


