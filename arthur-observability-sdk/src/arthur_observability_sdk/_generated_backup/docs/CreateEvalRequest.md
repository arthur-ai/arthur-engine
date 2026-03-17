# CreateEvalRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**model_name** | **str** | Name of the LLM model (e.g., &#39;gpt-4o&#39;, &#39;claude-3-sonnet&#39;) | 
**model_provider** | [**ModelProvider**](ModelProvider.md) | Provider of the LLM model (e.g., &#39;openai&#39;, &#39;anthropic&#39;, &#39;azure&#39;) | 
**instructions** | **str** | Instructions for the llm eval | 
**config** | [**LLMRequestConfigSettings**](LLMRequestConfigSettings.md) |  | [optional] 

## Example

```python
from _generated.models.create_eval_request import CreateEvalRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreateEvalRequest from a JSON string
create_eval_request_instance = CreateEvalRequest.from_json(json)
# print the JSON string representation of the object
print(CreateEvalRequest.to_json())

# convert the object into a dict
create_eval_request_dict = create_eval_request_instance.to_dict()
# create an instance of CreateEvalRequest from a dict
create_eval_request_from_dict = CreateEvalRequest.from_dict(create_eval_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


