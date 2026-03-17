# RagProviderCollectionResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**identifier** | **str** | Unique identifier of the collection. | 
**description** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.rag_provider_collection_response import RagProviderCollectionResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RagProviderCollectionResponse from a JSON string
rag_provider_collection_response_instance = RagProviderCollectionResponse.from_json(json)
# print the JSON string representation of the object
print(RagProviderCollectionResponse.to_json())

# convert the object into a dict
rag_provider_collection_response_dict = rag_provider_collection_response_instance.to_dict()
# create an instance of RagProviderCollectionResponse from a dict
rag_provider_collection_response_from_dict = RagProviderCollectionResponse.from_dict(rag_provider_collection_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


