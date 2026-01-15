# BaseCompletionRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variables** | [**List[VariableTemplateValue]**](VariableTemplateValue.md) |  | [optional] 

## Example

```python
from _generated.models.base_completion_request import BaseCompletionRequest

# TODO update the JSON string below
json = "{}"
# create an instance of BaseCompletionRequest from a JSON string
base_completion_request_instance = BaseCompletionRequest.from_json(json)
# print the JSON string representation of the object
print(BaseCompletionRequest.to_json())

# convert the object into a dict
base_completion_request_dict = base_completion_request_instance.to_dict()
# create an instance of BaseCompletionRequest from a dict
base_completion_request_from_dict = BaseCompletionRequest.from_dict(base_completion_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


