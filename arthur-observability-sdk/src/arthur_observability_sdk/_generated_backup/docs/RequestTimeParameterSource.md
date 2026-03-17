# RequestTimeParameterSource

Variable source from request-time parameters (e.g., tokens, API keys)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | Type of source: &#39;request_time_parameter&#39; | 

## Example

```python
from _generated.models.request_time_parameter_source import RequestTimeParameterSource

# TODO update the JSON string below
json = "{}"
# create an instance of RequestTimeParameterSource from a JSON string
request_time_parameter_source_instance = RequestTimeParameterSource.from_json(json)
# print the JSON string representation of the object
print(RequestTimeParameterSource.to_json())

# convert the object into a dict
request_time_parameter_source_dict = request_time_parameter_source_instance.to_dict()
# create an instance of RequestTimeParameterSource from a dict
request_time_parameter_source_from_dict = RequestTimeParameterSource.from_dict(request_time_parameter_source_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


