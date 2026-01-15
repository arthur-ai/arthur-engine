# ToolFunctionOutput


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | The name of the tool/function | 
**description** | **str** |  | [optional] 
**parameters** | [**JsonSchema**](JsonSchema.md) |  | [optional] 

## Example

```python
from _generated.models.tool_function_output import ToolFunctionOutput

# TODO update the JSON string below
json = "{}"
# create an instance of ToolFunctionOutput from a JSON string
tool_function_output_instance = ToolFunctionOutput.from_json(json)
# print the JSON string representation of the object
print(ToolFunctionOutput.to_json())

# convert the object into a dict
tool_function_output_dict = tool_function_output_instance.to_dict()
# create an instance of ToolFunctionOutput from a dict
tool_function_output_from_dict = ToolFunctionOutput.from_dict(tool_function_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


