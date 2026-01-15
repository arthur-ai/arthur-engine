# CreateAgenticPromptRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**messages** | [**List[OpenAIMessageInput]**](OpenAIMessageInput.md) | List of chat messages in OpenAI format (e.g., [{&#39;role&#39;: &#39;user&#39;, &#39;content&#39;: &#39;Hello&#39;}]) | 
**model_name** | **str** | Name of the LLM model (e.g., &#39;gpt-4o&#39;, &#39;claude-3-sonnet&#39;) | 
**model_provider** | [**ModelProvider**](ModelProvider.md) | Provider of the LLM model (e.g., &#39;openai&#39;, &#39;anthropic&#39;, &#39;azure&#39;) | 
**tools** | [**List[LLMToolInput]**](LLMToolInput.md) |  | [optional] 
**config** | [**LLMPromptRequestConfigSettings**](LLMPromptRequestConfigSettings.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.create_agentic_prompt_request import CreateAgenticPromptRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreateAgenticPromptRequest from a JSON string
create_agentic_prompt_request_instance = CreateAgenticPromptRequest.from_json(json)
# print the JSON string representation of the object
print(CreateAgenticPromptRequest.to_json())

# convert the object into a dict
create_agentic_prompt_request_dict = create_agentic_prompt_request_instance.to_dict()
# create an instance of CreateAgenticPromptRequest from a dict
create_agentic_prompt_request_from_dict = CreateAgenticPromptRequest.from_dict(create_agentic_prompt_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


