# WeaviateQueryResults

Response from Weaviate similarity text search

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**rag_provider** | **str** |  | [optional] [default to 'weaviate']
**objects** | [**List[WeaviateQueryResult]**](WeaviateQueryResult.md) | List of search result objects | 

## Example

```python
from _generated.models.weaviate_query_results import WeaviateQueryResults

# TODO update the JSON string below
json = "{}"
# create an instance of WeaviateQueryResults from a JSON string
weaviate_query_results_instance = WeaviateQueryResults.from_json(json)
# print the JSON string representation of the object
print(WeaviateQueryResults.to_json())

# convert the object into a dict
weaviate_query_results_dict = weaviate_query_results_instance.to_dict()
# create an instance of WeaviateQueryResults from a dict
weaviate_query_results_from_dict = WeaviateQueryResults.from_dict(weaviate_query_results_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


