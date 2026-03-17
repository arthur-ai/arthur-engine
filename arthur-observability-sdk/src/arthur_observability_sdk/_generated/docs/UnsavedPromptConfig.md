# UnsavedPromptConfig

Configuration for an unsaved prompt

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] [default to 'unsaved']
**auto_name** | **str** |  | [optional] 
**messages** | **List[Optional[object]]** | Prompt messages | 
**model_name** | **str** | LLM model name | 
**model_provider** | [**ModelProvider**](ModelProvider.md) | LLM provider | 
**tools** | **List[Optional[object]]** |  | [optional] 
**config** | **object** |  | [optional] 
**variables** | **List[str]** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.unsaved_prompt_config import UnsavedPromptConfig

# TODO update the JSON string below
json = "{}"
# create an instance of UnsavedPromptConfig from a JSON string
unsaved_prompt_config_instance = UnsavedPromptConfig.from_json(json)
# print the JSON string representation of the object
print(UnsavedPromptConfig.to_json())

# convert the object into a dict
unsaved_prompt_config_dict = unsaved_prompt_config_instance.to_dict()
# create an instance of UnsavedPromptConfig from a dict
unsaved_prompt_config_from_dict = UnsavedPromptConfig.from_dict(unsaved_prompt_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


