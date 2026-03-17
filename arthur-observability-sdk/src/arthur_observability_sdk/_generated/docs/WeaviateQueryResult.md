# WeaviateQueryResult

Individual search result from Weaviate

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**uuid** | **str** | Unique identifier of the result | 
**metadata** | [**WeaviateQueryResultMetadata**](WeaviateQueryResultMetadata.md) |  | [optional] 
**properties** | **object** | Properties of the result object | 
**vector** | [**Dict[str, WeaviateQueryResultVectorValue]**](WeaviateQueryResultVectorValue.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.weaviate_query_result import WeaviateQueryResult

# TODO update the JSON string below
json = "{}"
# create an instance of WeaviateQueryResult from a JSON string
weaviate_query_result_instance = WeaviateQueryResult.from_json(json)
# print the JSON string representation of the object
print(WeaviateQueryResult.to_json())

# convert the object into a dict
weaviate_query_result_dict = weaviate_query_result_instance.to_dict()
# create an instance of WeaviateQueryResult from a dict
weaviate_query_result_from_dict = WeaviateQueryResult.from_dict(weaviate_query_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


