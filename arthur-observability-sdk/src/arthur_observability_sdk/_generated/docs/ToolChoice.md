# ToolChoice

Tool choice configuration ('auto', 'none', 'required', or a specific tool selection)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | The type of tool choice. Should always be &#39;function&#39; | [optional] [default to 'function']
**function** | [**ToolChoiceFunction**](ToolChoiceFunction.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.tool_choice import ToolChoice

# TODO update the JSON string below
json = "{}"
# create an instance of ToolChoice from a JSON string
tool_choice_instance = ToolChoice.from_json(json)
# print the JSON string representation of the object
print(ToolChoice.to_json())

# convert the object into a dict
tool_choice_dict = tool_choice_instance.to_dict()
# create an instance of ToolChoice from a dict
tool_choice_from_dict = ToolChoice.from_dict(tool_choice_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


