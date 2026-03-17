# OpenAIMessageItem


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | [**OpenAIMessageType**](OpenAIMessageType.md) | Type of the message (either &#39;text&#39;, &#39;image_url&#39;, or &#39;input_audio&#39;) | 
**text** | **str** |  | [optional] 
**image_url** | [**ImageURL**](ImageURL.md) |  | [optional] 
**input_audio** | [**InputAudio**](InputAudio.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.open_ai_message_item import OpenAIMessageItem

# TODO update the JSON string below
json = "{}"
# create an instance of OpenAIMessageItem from a JSON string
open_ai_message_item_instance = OpenAIMessageItem.from_json(json)
# print the JSON string representation of the object
print(OpenAIMessageItem.to_json())

# convert the object into a dict
open_ai_message_item_dict = open_ai_message_item_instance.to_dict()
# create an instance of OpenAIMessageItem from a dict
open_ai_message_item_from_dict = OpenAIMessageItem.from_dict(open_ai_message_item_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


