# SearchRagProviderCollectionsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | The total number of RAG provider collections matching the parameters. | 
**rag_provider_collections** | [**List[RagProviderCollectionResponse]**](RagProviderCollectionResponse.md) |  | 

## Example

```python
from _generated.models.search_rag_provider_collections_response import SearchRagProviderCollectionsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SearchRagProviderCollectionsResponse from a JSON string
search_rag_provider_collections_response_instance = SearchRagProviderCollectionsResponse.from_json(json)
# print the JSON string representation of the object
print(SearchRagProviderCollectionsResponse.to_json())

# convert the object into a dict
search_rag_provider_collections_response_dict = search_rag_provider_collections_response_instance.to_dict()
# create an instance of SearchRagProviderCollectionsResponse from a dict
search_rag_provider_collections_response_from_dict = SearchRagProviderCollectionsResponse.from_dict(search_rag_provider_collections_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


