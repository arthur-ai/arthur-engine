# SavedPromptRenderingRequest

Request schema for rendering an unsaved agentic prompt with variables

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**completion_request** | [**VariableRenderingRequest**](VariableRenderingRequest.md) | Rendering configuration for the unsaved prompt | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.saved_prompt_rendering_request import SavedPromptRenderingRequest

# TODO update the JSON string below
json = "{}"
# create an instance of SavedPromptRenderingRequest from a JSON string
saved_prompt_rendering_request_instance = SavedPromptRenderingRequest.from_json(json)
# print the JSON string representation of the object
print(SavedPromptRenderingRequest.to_json())

# convert the object into a dict
saved_prompt_rendering_request_dict = saved_prompt_rendering_request_instance.to_dict()
# create an instance of SavedPromptRenderingRequest from a dict
saved_prompt_rendering_request_from_dict = SavedPromptRenderingRequest.from_dict(saved_prompt_rendering_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


