# MetadataQuery

Define which metadata should be returned in the query's results.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**creation_time** | **bool** |  | [optional] [default to False]
**last_update_time** | **bool** |  | [optional] [default to False]
**distance** | **bool** |  | [optional] [default to False]
**certainty** | **bool** |  | [optional] [default to False]
**score** | **bool** |  | [optional] [default to False]
**explain_score** | **bool** |  | [optional] [default to False]
**is_consistent** | **bool** |  | [optional] [default to False]

## Example

```python
from arthur_observability_sdk._generated.models.metadata_query import MetadataQuery

# TODO update the JSON string below
json = "{}"
# create an instance of MetadataQuery from a JSON string
metadata_query_instance = MetadataQuery.from_json(json)
# print the JSON string representation of the object
print(MetadataQuery.to_json())

# convert the object into a dict
metadata_query_dict = metadata_query_instance.to_dict()
# create an instance of MetadataQuery from a dict
metadata_query_from_dict = MetadataQuery.from_dict(metadata_query_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


