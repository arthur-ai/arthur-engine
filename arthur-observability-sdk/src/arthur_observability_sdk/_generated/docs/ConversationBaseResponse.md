# ConversationBaseResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**updated_at** | **datetime** |  | 

## Example

```python
from arthur_observability_sdk._generated.models.conversation_base_response import ConversationBaseResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ConversationBaseResponse from a JSON string
conversation_base_response_instance = ConversationBaseResponse.from_json(json)
# print the JSON string representation of the object
print(ConversationBaseResponse.to_json())

# convert the object into a dict
conversation_base_response_dict = conversation_base_response_instance.to_dict()
# create an instance of ConversationBaseResponse from a dict
conversation_base_response_from_dict = ConversationBaseResponse.from_dict(conversation_base_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


