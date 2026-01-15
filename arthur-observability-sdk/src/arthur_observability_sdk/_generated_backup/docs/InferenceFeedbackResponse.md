# InferenceFeedbackResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**inference_id** | **str** |  | 
**target** | [**InferenceFeedbackTarget**](InferenceFeedbackTarget.md) |  | 
**score** | **int** |  | 
**reason** | **str** |  | [optional] 
**user_id** | **str** |  | [optional] 
**created_at** | **datetime** |  | 
**updated_at** | **datetime** |  | 

## Example

```python
from _generated.models.inference_feedback_response import InferenceFeedbackResponse

# TODO update the JSON string below
json = "{}"
# create an instance of InferenceFeedbackResponse from a JSON string
inference_feedback_response_instance = InferenceFeedbackResponse.from_json(json)
# print the JSON string representation of the object
print(InferenceFeedbackResponse.to_json())

# convert the object into a dict
inference_feedback_response_dict = inference_feedback_response_instance.to_dict()
# create an instance of InferenceFeedbackResponse from a dict
inference_feedback_response_from_dict = InferenceFeedbackResponse.from_dict(inference_feedback_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


