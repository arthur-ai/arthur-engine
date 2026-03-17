# LLMConfigSettings


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**timeout** | **float** |  | [optional] 
**temperature** | **float** |  | [optional] 
**top_p** | **float** |  | [optional] 
**max_tokens** | **int** |  | [optional] 
**stop** | **str** |  | [optional] 
**presence_penalty** | **float** |  | [optional] 
**frequency_penalty** | **float** |  | [optional] 
**seed** | **int** |  | [optional] 
**logprobs** | **bool** |  | [optional] 
**top_logprobs** | **int** |  | [optional] 
**logit_bias** | [**List[LogitBiasItem]**](LogitBiasItem.md) |  | [optional] 
**max_completion_tokens** | **int** |  | [optional] 
**reasoning_effort** | [**ReasoningEffortEnum**](ReasoningEffortEnum.md) |  | [optional] 
**thinking** | [**AnthropicThinkingParam**](AnthropicThinkingParam.md) |  | [optional] 
**tool_choice** | [**ToolChoice**](ToolChoice.md) |  | [optional] 
**response_format** | [**LLMResponseFormatOutput**](LLMResponseFormatOutput.md) |  | [optional] 
**stream_options** | [**StreamOptions**](StreamOptions.md) |  | [optional] 

## Example

```python
from _generated.models.llm_config_settings import LLMConfigSettings

# TODO update the JSON string below
json = "{}"
# create an instance of LLMConfigSettings from a JSON string
llm_config_settings_instance = LLMConfigSettings.from_json(json)
# print the JSON string representation of the object
print(LLMConfigSettings.to_json())

# convert the object into a dict
llm_config_settings_dict = llm_config_settings_instance.to_dict()
# create an instance of LLMConfigSettings from a dict
llm_config_settings_from_dict = LLMConfigSettings.from_dict(llm_config_settings_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


