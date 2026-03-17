# SearchRulesRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**rule_ids** | **List[str]** |  | [optional] 
**rule_scopes** | [**List[RuleScope]**](RuleScope.md) |  | [optional] 
**prompt_enabled** | **bool** |  | [optional] 
**response_enabled** | **bool** |  | [optional] 
**rule_types** | [**List[RuleType]**](RuleType.md) |  | [optional] 

## Example

```python
from _generated.models.search_rules_request import SearchRulesRequest

# TODO update the JSON string below
json = "{}"
# create an instance of SearchRulesRequest from a JSON string
search_rules_request_instance = SearchRulesRequest.from_json(json)
# print the JSON string representation of the object
print(SearchRulesRequest.to_json())

# convert the object into a dict
search_rules_request_dict = search_rules_request_instance.to_dict()
# create an instance of SearchRulesRequest from a dict
search_rules_request_from_dict = SearchRulesRequest.from_dict(search_rules_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


