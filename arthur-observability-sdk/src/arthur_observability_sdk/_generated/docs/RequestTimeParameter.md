# RequestTimeParameter

Request-time parameter with name and value (e.g., API keys, tokens)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the request-time parameter (must match variable_name in template_variable_mapping) | 
**value** | **str** | Value of the request-time parameter (not saved, provided at execution time) | 

## Example

```python
from arthur_observability_sdk._generated.models.request_time_parameter import RequestTimeParameter

# TODO update the JSON string below
json = "{}"
# create an instance of RequestTimeParameter from a JSON string
request_time_parameter_instance = RequestTimeParameter.from_json(json)
# print the JSON string representation of the object
print(RequestTimeParameter.to_json())

# convert the object into a dict
request_time_parameter_dict = request_time_parameter_instance.to_dict()
# create an instance of RequestTimeParameter from a dict
request_time_parameter_from_dict = RequestTimeParameter.from_dict(request_time_parameter_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


