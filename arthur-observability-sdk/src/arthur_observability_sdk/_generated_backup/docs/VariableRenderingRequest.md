# VariableRenderingRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variables** | [**List[VariableTemplateValue]**](VariableTemplateValue.md) |  | [optional] 
**strict** | **bool** |  | [optional] 

## Example

```python
from _generated.models.variable_rendering_request import VariableRenderingRequest

# TODO update the JSON string below
json = "{}"
# create an instance of VariableRenderingRequest from a JSON string
variable_rendering_request_instance = VariableRenderingRequest.from_json(json)
# print the JSON string representation of the object
print(VariableRenderingRequest.to_json())

# convert the object into a dict
variable_rendering_request_dict = variable_rendering_request_instance.to_dict()
# create an instance of VariableRenderingRequest from a dict
variable_rendering_request_from_dict = VariableRenderingRequest.from_dict(variable_rendering_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


