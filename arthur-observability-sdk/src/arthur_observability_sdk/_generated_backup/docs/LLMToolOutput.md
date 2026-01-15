# LLMToolOutput


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | The type of tool. Should always be &#39;function&#39; | [optional] [default to 'function']
**function** | [**ToolFunctionOutput**](ToolFunctionOutput.md) | The function definition | 
**strict** | **bool** |  | [optional] 

## Example

```python
from _generated.models.llm_tool_output import LLMToolOutput

# TODO update the JSON string below
json = "{}"
# create an instance of LLMToolOutput from a JSON string
llm_tool_output_instance = LLMToolOutput.from_json(json)
# print the JSON string representation of the object
print(LLMToolOutput.to_json())

# convert the object into a dict
llm_tool_output_dict = llm_tool_output_instance.to_dict()
# create an instance of LLMToolOutput from a dict
llm_tool_output_from_dict = LLMToolOutput.from_dict(llm_tool_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


