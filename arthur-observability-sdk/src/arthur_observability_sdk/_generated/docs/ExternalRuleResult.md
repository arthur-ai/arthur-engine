# ExternalRuleResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  ID of the rule | 
**name** | **str** | Name of the rule | 
**rule_type** | [**RuleType**](RuleType.md) | Type of the rule | 
**scope** | [**RuleScope**](RuleScope.md) | Scope of the rule. The rule can be set at default level or task level. | 
**result** | [**RuleResultEnum**](RuleResultEnum.md) | Result if the rule | 
**latency_ms** | **int** | Duration in millisesconds of rule execution | 
**details** | [**Details**](Details.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.external_rule_result import ExternalRuleResult

# TODO update the JSON string below
json = "{}"
# create an instance of ExternalRuleResult from a JSON string
external_rule_result_instance = ExternalRuleResult.from_json(json)
# print the JSON string representation of the object
print(ExternalRuleResult.to_json())

# convert the object into a dict
external_rule_result_dict = external_rule_result_instance.to_dict()
# create an instance of ExternalRuleResult from a dict
external_rule_result_from_dict = ExternalRuleResult.from_dict(external_rule_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


