# ToolFunctionInput


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | The name of the tool/function | 
**description** | **str** |  | [optional] 
**parameters** | [**JsonSchema**](JsonSchema.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.tool_function_input import ToolFunctionInput

# TODO update the JSON string below
json = "{}"
# create an instance of ToolFunctionInput from a JSON string
tool_function_input_instance = ToolFunctionInput.from_json(json)
# print the JSON string representation of the object
print(ToolFunctionInput.to_json())

# convert the object into a dict
tool_function_input_dict = tool_function_input_instance.to_dict()
# create an instance of ToolFunctionInput from a dict
tool_function_input_from_dict = ToolFunctionInput.from_dict(tool_function_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


