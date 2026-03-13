# WeaviateQueryResultMetadata

Metadata from weaviate for a vector object: https://weaviate-python-client.readthedocs.io/en/latest/weaviate.collections.classes.html#module-weaviate.collections.classes.internal

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**creation_time** | **datetime** |  | [optional] 
**last_update_time** | **datetime** |  | [optional] 
**distance** | **float** |  | [optional] 
**certainty** | **float** |  | [optional] 
**score** | **float** |  | [optional] 
**explain_score** | **str** |  | [optional] 
**is_consistent** | **bool** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.weaviate_query_result_metadata import WeaviateQueryResultMetadata

# TODO update the JSON string below
json = "{}"
# create an instance of WeaviateQueryResultMetadata from a JSON string
weaviate_query_result_metadata_instance = WeaviateQueryResultMetadata.from_json(json)
# print the JSON string representation of the object
print(WeaviateQueryResultMetadata.to_json())

# convert the object into a dict
weaviate_query_result_metadata_dict = weaviate_query_result_metadata_instance.to_dict()
# create an instance of WeaviateQueryResultMetadata from a dict
weaviate_query_result_metadata_from_dict = WeaviateQueryResultMetadata.from_dict(weaviate_query_result_metadata_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


