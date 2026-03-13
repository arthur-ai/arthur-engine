# AgenticPrompt


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the agentic prompt | 
**messages** | [**List[OpenAIMessageOutput]**](OpenAIMessageOutput.md) | List of chat messages in OpenAI format (e.g., [{&#39;role&#39;: &#39;user&#39;, &#39;content&#39;: &#39;Hello&#39;}]) | 
**model_name** | **str** | Name of the LLM model (e.g., &#39;gpt-4o&#39;, &#39;claude-3-sonnet&#39;) | 
**model_provider** | [**ModelProvider**](ModelProvider.md) | Provider of the LLM model (e.g., &#39;openai&#39;, &#39;anthropic&#39;, &#39;azure&#39;) | 
**version** | **int** | Version of the agentic prompt | [optional] [default to 1]
**tools** | [**List[LLMToolOutput]**](LLMToolOutput.md) |  | [optional] 
**variables** | **List[str]** | List of variable names for the agentic prompt | [optional] 
**tags** | **List[str]** | List of tags for this agentic prompt version | [optional] 
**config** | [**LLMConfigSettings**](LLMConfigSettings.md) |  | [optional] 
**created_at** | **datetime** | Timestamp when the prompt was created. | 
**deleted_at** | **datetime** |  | [optional] 

## Example

```python
from _generated.models.agentic_prompt import AgenticPrompt

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticPrompt from a JSON string
agentic_prompt_instance = AgenticPrompt.from_json(json)
# print the JSON string representation of the object
print(AgenticPrompt.to_json())

# convert the object into a dict
agentic_prompt_dict = agentic_prompt_instance.to_dict()
# create an instance of AgenticPrompt from a dict
agentic_prompt_from_dict = AgenticPrompt.from_dict(agentic_prompt_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


