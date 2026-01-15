# ToolCall


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | The type of tool call. Currently the only type supported is &#39;function&#39;. | [optional] [default to 'function']
**id** | **str** | Unique identifier for the tool call | 
**function** | [**ToolCallFunction**](ToolCallFunction.md) | Function details | 

## Example

```python
from _generated.models.tool_call import ToolCall

# TODO update the JSON string below
json = "{}"
# create an instance of ToolCall from a JSON string
tool_call_instance = ToolCall.from_json(json)
# print the JSON string representation of the object
print(ToolCall.to_json())

# convert the object into a dict
tool_call_dict = tool_call_instance.to_dict()
# create an instance of ToolCall from a dict
tool_call_from_dict = ToolCall.from_dict(tool_call_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


