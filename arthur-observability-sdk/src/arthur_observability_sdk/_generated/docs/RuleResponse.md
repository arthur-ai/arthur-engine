# RuleResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | ID of the Rule | 
**name** | **str** | Name of the Rule | 
**type** | [**RuleType**](RuleType.md) | Type of Rule | 
**apply_to_prompt** | **bool** | Rule applies to prompt | 
**apply_to_response** | **bool** | Rule applies to response | 
**enabled** | **bool** |  | [optional] 
**scope** | [**RuleScope**](RuleScope.md) | Scope of the rule. The rule can be set at default level or task level. | 
**created_at** | **int** | Time the rule was created in unix milliseconds | 
**updated_at** | **int** | Time the rule was updated in unix milliseconds | 
**config** | [**Config**](Config.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.rule_response import RuleResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RuleResponse from a JSON string
rule_response_instance = RuleResponse.from_json(json)
# print the JSON string representation of the object
print(RuleResponse.to_json())

# convert the object into a dict
rule_response_dict = rule_response_instance.to_dict()
# create an instance of RuleResponse from a dict
rule_response_from_dict = RuleResponse.from_dict(rule_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


