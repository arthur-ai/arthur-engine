# ReturnMetadata

Specify metadata fields to return.

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
from _generated.models.return_metadata import ReturnMetadata

# TODO update the JSON string below
json = "{}"
# create an instance of ReturnMetadata from a JSON string
return_metadata_instance = ReturnMetadata.from_json(json)
# print the JSON string representation of the object
print(ReturnMetadata.to_json())

# convert the object into a dict
return_metadata_dict = return_metadata_instance.to_dict()
# create an instance of ReturnMetadata from a dict
return_metadata_from_dict = ReturnMetadata.from_dict(return_metadata_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


