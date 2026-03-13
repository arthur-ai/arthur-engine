# LLMEval


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the llm eval | 
**model_name** | **str** | Name of the LLM model (e.g., &#39;gpt-4o&#39;, &#39;claude-3-sonnet&#39;) | 
**model_provider** | [**ModelProvider**](ModelProvider.md) | Provider of the LLM model (e.g., &#39;openai&#39;, &#39;anthropic&#39;, &#39;azure&#39;) | 
**instructions** | **str** | Instructions for the llm eval | 
**variables** | **List[str]** | List of variable names for the llm eval | [optional] 
**tags** | **List[str]** | List of tags for this llm eval version | [optional] 
**config** | [**LLMBaseConfigSettings**](LLMBaseConfigSettings.md) |  | [optional] 
**created_at** | **datetime** | Timestamp when the llm eval was created. | 
**deleted_at** | **datetime** |  | [optional] 
**version** | **int** | Version of the llm eval | [optional] [default to 1]

## Example

```python
from arthur_observability_sdk._generated.models.llm_eval import LLMEval

# TODO update the JSON string below
json = "{}"
# create an instance of LLMEval from a JSON string
llm_eval_instance = LLMEval.from_json(json)
# print the JSON string representation of the object
print(LLMEval.to_json())

# convert the object into a dict
llm_eval_dict = llm_eval_instance.to_dict()
# create an instance of LLMEval from a dict
llm_eval_from_dict = LLMEval.from_dict(llm_eval_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


