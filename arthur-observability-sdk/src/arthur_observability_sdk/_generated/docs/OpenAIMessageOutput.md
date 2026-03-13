# OpenAIMessageOutput

The message schema class for the prompts playground. This class adheres to OpenAI's message schema.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**role** | [**MessageRole**](MessageRole.md) | Role of the message | 
**name** | **str** |  | [optional] 
**content** | [**Content**](Content.md) |  | [optional] 
**tool_calls** | [**List[ToolCall]**](ToolCall.md) |  | [optional] 
**tool_call_id** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.open_ai_message_output import OpenAIMessageOutput

# TODO update the JSON string below
json = "{}"
# create an instance of OpenAIMessageOutput from a JSON string
open_ai_message_output_instance = OpenAIMessageOutput.from_json(json)
# print the JSON string representation of the object
print(OpenAIMessageOutput.to_json())

# convert the object into a dict
open_ai_message_output_dict = open_ai_message_output_instance.to_dict()
# create an instance of OpenAIMessageOutput from a dict
open_ai_message_output_from_dict = OpenAIMessageOutput.from_dict(open_ai_message_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


