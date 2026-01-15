# PromptOutput

Output from a prompt execution

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**content** | **str** | Content of the prompt response | 
**tool_calls** | **List[object]** | Tool calls made by the prompt | [optional] 
**cost** | **str** | Cost of the prompt execution | 

## Example

```python
from arthur_observability_sdk._generated.models.prompt_output import PromptOutput

# TODO update the JSON string below
json = "{}"
# create an instance of PromptOutput from a JSON string
prompt_output_instance = PromptOutput.from_json(json)
# print the JSON string representation of the object
print(PromptOutput.to_json())

# convert the object into a dict
prompt_output_dict = prompt_output_instance.to_dict()
# create an instance of PromptOutput from a dict
prompt_output_from_dict = PromptOutput.from_dict(prompt_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


