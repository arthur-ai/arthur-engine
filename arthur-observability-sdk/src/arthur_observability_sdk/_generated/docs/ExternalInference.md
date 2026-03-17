# ExternalInference


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**result** | [**RuleResultEnum**](RuleResultEnum.md) |  | 
**created_at** | **int** |  | 
**updated_at** | **int** |  | 
**task_id** | **str** |  | [optional] 
**task_name** | **str** |  | [optional] 
**conversation_id** | **str** |  | [optional] 
**inference_prompt** | [**ExternalInferencePrompt**](ExternalInferencePrompt.md) |  | 
**inference_response** | [**ExternalInferenceResponse**](ExternalInferenceResponse.md) |  | [optional] 
**inference_feedback** | [**List[InferenceFeedbackResponse]**](InferenceFeedbackResponse.md) |  | 
**user_id** | **str** |  | [optional] 
**model_name** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.external_inference import ExternalInference

# TODO update the JSON string below
json = "{}"
# create an instance of ExternalInference from a JSON string
external_inference_instance = ExternalInference.from_json(json)
# print the JSON string representation of the object
print(ExternalInference.to_json())

# convert the object into a dict
external_inference_dict = external_inference_instance.to_dict()
# create an instance of ExternalInference from a dict
external_inference_from_dict = ExternalInference.from_dict(external_inference_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


