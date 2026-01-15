# UnsavedPromptVariablesListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variables** | **List[str]** | List of variables needed to run an unsaved prompt | 

## Example

```python
from _generated.models.unsaved_prompt_variables_list_response import UnsavedPromptVariablesListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of UnsavedPromptVariablesListResponse from a JSON string
unsaved_prompt_variables_list_response_instance = UnsavedPromptVariablesListResponse.from_json(json)
# print the JSON string representation of the object
print(UnsavedPromptVariablesListResponse.to_json())

# convert the object into a dict
unsaved_prompt_variables_list_response_dict = unsaved_prompt_variables_list_response_instance.to_dict()
# create an instance of UnsavedPromptVariablesListResponse from a dict
unsaved_prompt_variables_list_response_from_dict = UnsavedPromptVariablesListResponse.from_dict(unsaved_prompt_variables_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


