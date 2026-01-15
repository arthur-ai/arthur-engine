# ExternalDocument


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**name** | **str** |  | 
**type** | **str** |  | 
**owner_id** | **str** |  | 

## Example

```python
from arthur_observability_sdk._generated.models.external_document import ExternalDocument

# TODO update the JSON string below
json = "{}"
# create an instance of ExternalDocument from a JSON string
external_document_instance = ExternalDocument.from_json(json)
# print the JSON string representation of the object
print(ExternalDocument.to_json())

# convert the object into a dict
external_document_dict = external_document_instance.to_dict()
# create an instance of ExternalDocument from a dict
external_document_from_dict = ExternalDocument.from_dict(external_document_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


