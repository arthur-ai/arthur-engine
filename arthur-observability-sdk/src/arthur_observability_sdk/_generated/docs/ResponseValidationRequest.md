# ResponseValidationRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**response** | **str** | LLM Response to be validated by GenAI Engine | 
**context** | **str** |  | [optional] 
**model_name** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.response_validation_request import ResponseValidationRequest

# TODO update the JSON string below
json = "{}"
# create an instance of ResponseValidationRequest from a JSON string
response_validation_request_instance = ResponseValidationRequest.from_json(json)
# print the JSON string representation of the object
print(ResponseValidationRequest.to_json())

# convert the object into a dict
response_validation_request_dict = response_validation_request_instance.to_dict()
# create an instance of ResponseValidationRequest from a dict
response_validation_request_from_dict = ResponseValidationRequest.from_dict(response_validation_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


