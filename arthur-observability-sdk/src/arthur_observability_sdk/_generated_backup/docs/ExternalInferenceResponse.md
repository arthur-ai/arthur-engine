# ExternalInferenceResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**inference_id** | **str** |  | 
**result** | [**RuleResultEnum**](RuleResultEnum.md) |  | 
**created_at** | **int** |  | 
**updated_at** | **int** |  | 
**message** | **str** |  | 
**context** | **str** |  | [optional] 
**response_rule_results** | [**List[ExternalRuleResult]**](ExternalRuleResult.md) |  | 
**tokens** | **int** |  | [optional] 
**model_name** | **str** |  | [optional] 

## Example

```python
from _generated.models.external_inference_response import ExternalInferenceResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ExternalInferenceResponse from a JSON string
external_inference_response_instance = ExternalInferenceResponse.from_json(json)
# print the JSON string representation of the object
print(ExternalInferenceResponse.to_json())

# convert the object into a dict
external_inference_response_dict = external_inference_response_instance.to_dict()
# create an instance of ExternalInferenceResponse from a dict
external_inference_response_from_dict = ExternalInferenceResponse.from_dict(external_inference_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


