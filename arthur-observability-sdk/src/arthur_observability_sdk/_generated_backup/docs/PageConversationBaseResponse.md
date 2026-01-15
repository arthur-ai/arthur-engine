# PageConversationBaseResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**items** | [**List[ConversationBaseResponse]**](ConversationBaseResponse.md) |  | 
**total** | **int** |  | 
**page** | **int** |  | 
**size** | **int** |  | 
**pages** | **int** |  | 

## Example

```python
from _generated.models.page_conversation_base_response import PageConversationBaseResponse

# TODO update the JSON string below
json = "{}"
# create an instance of PageConversationBaseResponse from a JSON string
page_conversation_base_response_instance = PageConversationBaseResponse.from_json(json)
# print the JSON string representation of the object
print(PageConversationBaseResponse.to_json())

# convert the object into a dict
page_conversation_base_response_dict = page_conversation_base_response_instance.to_dict()
# create an instance of PageConversationBaseResponse from a dict
page_conversation_base_response_from_dict = PageConversationBaseResponse.from_dict(page_conversation_base_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


