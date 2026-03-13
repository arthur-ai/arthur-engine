# ContinuousEvalCreateRequest

Request schema for creating a continuous eval

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the continuous eval | 
**description** | **str** |  | [optional] 
**llm_eval_name** | **str** | Name of the llm eval to create the continuous eval for | 
**llm_eval_version** | [**LlmEvalVersion**](LlmEvalVersion.md) |  | 
**transform_id** | **str** | ID of the transform to create the continuous eval for | 

## Example

```python
from arthur_observability_sdk._generated.models.continuous_eval_create_request import ContinuousEvalCreateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of ContinuousEvalCreateRequest from a JSON string
continuous_eval_create_request_instance = ContinuousEvalCreateRequest.from_json(json)
# print the JSON string representation of the object
print(ContinuousEvalCreateRequest.to_json())

# convert the object into a dict
continuous_eval_create_request_dict = continuous_eval_create_request_instance.to_dict()
# create an instance of ContinuousEvalCreateRequest from a dict
continuous_eval_create_request_from_dict = ContinuousEvalCreateRequest.from_dict(continuous_eval_create_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


