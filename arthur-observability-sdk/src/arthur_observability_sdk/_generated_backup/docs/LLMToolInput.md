# LLMToolInput


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | The type of tool. Should always be &#39;function&#39; | [optional] [default to 'function']
**function** | [**ToolFunctionInput**](ToolFunctionInput.md) | The function definition | 
**strict** | **bool** |  | [optional] 

## Example

```python
from _generated.models.llm_tool_input import LLMToolInput

# TODO update the JSON string below
json = "{}"
# create an instance of LLMToolInput from a JSON string
llm_tool_input_instance = LLMToolInput.from_json(json)
# print the JSON string representation of the object
print(LLMToolInput.to_json())

# convert the object into a dict
llm_tool_input_dict = llm_tool_input_instance.to_dict()
# create an instance of LLMToolInput from a dict
llm_tool_input_from_dict = LLMToolInput.from_dict(llm_tool_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


