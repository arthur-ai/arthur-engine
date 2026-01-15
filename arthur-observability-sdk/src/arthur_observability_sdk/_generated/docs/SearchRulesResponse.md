# SearchRulesResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | The total number of rules matching the parameters | 
**rules** | [**List[RuleResponse]**](RuleResponse.md) | List of rules matching the search filters. Length is less than or equal to page_size parameter | 

## Example

```python
from arthur_observability_sdk._generated.models.search_rules_response import SearchRulesResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SearchRulesResponse from a JSON string
search_rules_response_instance = SearchRulesResponse.from_json(json)
# print the JSON string representation of the object
print(SearchRulesResponse.to_json())

# convert the object into a dict
search_rules_response_dict = search_rules_response_instance.to_dict()
# create an instance of SearchRulesResponse from a dict
search_rules_response_from_dict = SearchRulesResponse.from_dict(search_rules_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


