# ExternalInferencePrompt


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**inference_id** | **str** |  | 
**result** | [**RuleResultEnum**](RuleResultEnum.md) |  | 
**created_at** | **int** |  | 
**updated_at** | **int** |  | 
**message** | **str** |  | 
**prompt_rule_results** | [**List[ExternalRuleResult]**](ExternalRuleResult.md) |  | 
**tokens** | **int** |  | [optional] 

## Example

```python
from _generated.models.external_inference_prompt import ExternalInferencePrompt

# TODO update the JSON string below
json = "{}"
# create an instance of ExternalInferencePrompt from a JSON string
external_inference_prompt_instance = ExternalInferencePrompt.from_json(json)
# print the JSON string representation of the object
print(ExternalInferencePrompt.to_json())

# convert the object into a dict
external_inference_prompt_dict = external_inference_prompt_instance.to_dict()
# create an instance of ExternalInferencePrompt from a dict
external_inference_prompt_from_dict = ExternalInferencePrompt.from_dict(external_inference_prompt_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


