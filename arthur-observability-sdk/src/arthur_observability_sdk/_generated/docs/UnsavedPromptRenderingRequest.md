# UnsavedPromptRenderingRequest

Request schema for rendering an unsaved agentic prompt with variables

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**completion_request** | [**VariableRenderingRequest**](VariableRenderingRequest.md) | Rendering configuration for the unsaved prompt | [optional] 
**messages** | [**List[OpenAIMessageInput]**](OpenAIMessageInput.md) | List of chat messages in OpenAI format (e.g., [{&#39;role&#39;: &#39;user&#39;, &#39;content&#39;: &#39;Hello&#39;}]) | 

## Example

```python
from arthur_observability_sdk._generated.models.unsaved_prompt_rendering_request import UnsavedPromptRenderingRequest

# TODO update the JSON string below
json = "{}"
# create an instance of UnsavedPromptRenderingRequest from a JSON string
unsaved_prompt_rendering_request_instance = UnsavedPromptRenderingRequest.from_json(json)
# print the JSON string representation of the object
print(UnsavedPromptRenderingRequest.to_json())

# convert the object into a dict
unsaved_prompt_rendering_request_dict = unsaved_prompt_rendering_request_instance.to_dict()
# create an instance of UnsavedPromptRenderingRequest from a dict
unsaved_prompt_rendering_request_from_dict = UnsavedPromptRenderingRequest.from_dict(unsaved_prompt_rendering_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


