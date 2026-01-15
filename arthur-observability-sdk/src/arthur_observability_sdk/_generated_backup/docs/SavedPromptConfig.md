# SavedPromptConfig

Configuration for a saved prompt

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] [default to 'saved']
**name** | **str** | Name of the saved prompt | 
**version** | **int** | Version of the saved prompt | 

## Example

```python
from _generated.models.saved_prompt_config import SavedPromptConfig

# TODO update the JSON string below
json = "{}"
# create an instance of SavedPromptConfig from a JSON string
saved_prompt_config_instance = SavedPromptConfig.from_json(json)
# print the JSON string representation of the object
print(SavedPromptConfig.to_json())

# convert the object into a dict
saved_prompt_config_dict = saved_prompt_config_instance.to_dict()
# create an instance of SavedPromptConfig from a dict
saved_prompt_config_from_dict = SavedPromptConfig.from_dict(saved_prompt_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


