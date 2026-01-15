# RagProviderQueryResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**response** | [**WeaviateQueryResults**](WeaviateQueryResults.md) |  | 

## Example

```python
from _generated.models.rag_provider_query_response import RagProviderQueryResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RagProviderQueryResponse from a JSON string
rag_provider_query_response_instance = RagProviderQueryResponse.from_json(json)
# print the JSON string representation of the object
print(RagProviderQueryResponse.to_json())

# convert the object into a dict
rag_provider_query_response_dict = rag_provider_query_response_instance.to_dict()
# create an instance of RagProviderQueryResponse from a dict
rag_provider_query_response_from_dict = RagProviderQueryResponse.from_dict(rag_provider_query_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


