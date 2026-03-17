# FeedbackRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**target** | [**InferenceFeedbackTarget**](InferenceFeedbackTarget.md) |  | 
**score** | **int** |  | 
**reason** | **str** |  | 
**user_id** | **str** |  | [optional] 

## Example

```python
from _generated.models.feedback_request import FeedbackRequest

# TODO update the JSON string below
json = "{}"
# create an instance of FeedbackRequest from a JSON string
feedback_request_instance = FeedbackRequest.from_json(json)
# print the JSON string representation of the object
print(FeedbackRequest.to_json())

# convert the object into a dict
feedback_request_dict = feedback_request_instance.to_dict()
# create an instance of FeedbackRequest from a dict
feedback_request_from_dict = FeedbackRequest.from_dict(feedback_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


