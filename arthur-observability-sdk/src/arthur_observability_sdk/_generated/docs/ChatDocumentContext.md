# ChatDocumentContext


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**seq_num** | **int** |  | 
**context** | **str** |  | 

## Example

```python
from arthur_observability_sdk._generated.models.chat_document_context import ChatDocumentContext

# TODO update the JSON string below
json = "{}"
# create an instance of ChatDocumentContext from a JSON string
chat_document_context_instance = ChatDocumentContext.from_json(json)
# print the JSON string representation of the object
print(ChatDocumentContext.to_json())

# convert the object into a dict
chat_document_context_dict = chat_document_context_instance.to_dict()
# create an instance of ChatDocumentContext from a dict
chat_document_context_from_dict = ChatDocumentContext.from_dict(chat_document_context_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


