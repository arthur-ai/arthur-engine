# UpdateContinuousEvalRequest

Request schema for creating a continuous eval

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**description** | **str** |  | [optional] 
**llm_eval_name** | **str** |  | [optional] 
**llm_eval_version** | [**LlmEvalVersion1**](LlmEvalVersion1.md) |  | [optional] 
**transform_id** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.update_continuous_eval_request import UpdateContinuousEvalRequest

# TODO update the JSON string below
json = "{}"
# create an instance of UpdateContinuousEvalRequest from a JSON string
update_continuous_eval_request_instance = UpdateContinuousEvalRequest.from_json(json)
# print the JSON string representation of the object
print(UpdateContinuousEvalRequest.to_json())

# convert the object into a dict
update_continuous_eval_request_dict = update_continuous_eval_request_instance.to_dict()
# create an instance of UpdateContinuousEvalRequest from a dict
update_continuous_eval_request_from_dict = UpdateContinuousEvalRequest.from_dict(update_continuous_eval_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


