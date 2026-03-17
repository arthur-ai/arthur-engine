# NewRuleRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the rule | 
**type** | **str** | Type of the rule. It can only be one of KeywordRule, RegexRule, ModelSensitiveDataRule, ModelHallucinationRule, ModelHallucinationRuleV2, PromptInjectionRule, PIIDataRule | 
**apply_to_prompt** | **bool** | Boolean value to enable or disable the rule for llm prompt | 
**apply_to_response** | **bool** | Boolean value to enable or disable the rule for llm response | 
**config** | [**Config**](Config.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.new_rule_request import NewRuleRequest

# TODO update the JSON string below
json = "{}"
# create an instance of NewRuleRequest from a JSON string
new_rule_request_instance = NewRuleRequest.from_json(json)
# print the JSON string representation of the object
print(NewRuleRequest.to_json())

# convert the object into a dict
new_rule_request_dict = new_rule_request_instance.to_dict()
# create an instance of NewRuleRequest from a dict
new_rule_request_from_dict = NewRuleRequest.from_dict(new_rule_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


