# CompletionRequest

Request schema for running an unsaved agentic prompt

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**messages** | [**List[OpenAIMessageInput]**](OpenAIMessageInput.md) | List of chat messages in OpenAI format (e.g., [{&#39;role&#39;: &#39;user&#39;, &#39;content&#39;: &#39;Hello&#39;}]) | 
**model_name** | **str** | Name of the LLM model (e.g., &#39;gpt-4o&#39;, &#39;claude-3-sonnet&#39;) | 
**model_provider** | [**ModelProvider**](ModelProvider.md) | Provider of the LLM model (e.g., &#39;openai&#39;, &#39;anthropic&#39;, &#39;azure&#39;) | 
**tools** | [**List[LLMToolInput]**](LLMToolInput.md) |  | [optional] 
**config** | [**LLMPromptRequestConfigSettings**](LLMPromptRequestConfigSettings.md) |  | [optional] 
**completion_request** | [**PromptCompletionRequest**](PromptCompletionRequest.md) | Run configuration for the unsaved prompt | [optional] 

## Example

```python
from _generated.models.completion_request import CompletionRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CompletionRequest from a JSON string
completion_request_instance = CompletionRequest.from_json(json)
# print the JSON string representation of the object
print(CompletionRequest.to_json())

# convert the object into a dict
completion_request_dict = completion_request_instance.to_dict()
# create an instance of CompletionRequest from a dict
completion_request_from_dict = CompletionRequest.from_dict(completion_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


