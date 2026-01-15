# TokenUsageResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**rule_type** | **str** |  | [optional] 
**task_id** | **str** |  | [optional] 
**count** | [**TokenUsageCount**](TokenUsageCount.md) |  | 

## Example

```python
from arthur_observability_sdk._generated.models.token_usage_response import TokenUsageResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TokenUsageResponse from a JSON string
token_usage_response_instance = TokenUsageResponse.from_json(json)
# print the JSON string representation of the object
print(TokenUsageResponse.to_json())

# convert the object into a dict
token_usage_response_dict = token_usage_response_instance.to_dict()
# create an instance of TokenUsageResponse from a dict
token_usage_response_from_dict = TokenUsageResponse.from_dict(token_usage_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


