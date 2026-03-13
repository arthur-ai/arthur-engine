# UnsavedPromptVariablesRequest

Request schema for getting the list of variables needed from an unsaved prompt's messages

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**messages** | [**List[OpenAIMessageInput]**](OpenAIMessageInput.md) | List of chat messages in OpenAI format (e.g., [{&#39;role&#39;: &#39;user&#39;, &#39;content&#39;: &#39;Hello&#39;}]) | 

## Example

```python
from arthur_observability_sdk._generated.models.unsaved_prompt_variables_request import UnsavedPromptVariablesRequest

# TODO update the JSON string below
json = "{}"
# create an instance of UnsavedPromptVariablesRequest from a JSON string
unsaved_prompt_variables_request_instance = UnsavedPromptVariablesRequest.from_json(json)
# print the JSON string representation of the object
print(UnsavedPromptVariablesRequest.to_json())

# convert the object into a dict
unsaved_prompt_variables_request_dict = unsaved_prompt_variables_request_instance.to_dict()
# create an instance of UnsavedPromptVariablesRequest from a dict
unsaved_prompt_variables_request_from_dict = UnsavedPromptVariablesRequest.from_dict(unsaved_prompt_variables_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


