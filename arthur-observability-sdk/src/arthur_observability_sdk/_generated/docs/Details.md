# Details

Details of the rule output

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**score** | **bool** |  | [optional] 
**message** | **str** |  | [optional] 
**keyword_matches** | [**List[KeywordSpanResponse]**](KeywordSpanResponse.md) | Each keyword in this list corresponds to a keyword that was both configured in the rule that was run and found in the input text. | [optional] [default to []]
**regex_matches** | [**List[RegexSpanResponse]**](RegexSpanResponse.md) | Each string in this list corresponds to a matching span from the input text that matches the configured regex rule. | [optional] [default to []]
**claims** | [**List[HallucinationClaimResponse]**](HallucinationClaimResponse.md) |  | 
**pii_entities** | [**List[PIIEntitySpanResponse]**](PIIEntitySpanResponse.md) |  | 
**toxicity_score** | **float** |  | [optional] 
**toxicity_violation_type** | [**ToxicityViolationType**](ToxicityViolationType.md) |  | 

## Example

```python
from arthur_observability_sdk._generated.models.details import Details

# TODO update the JSON string below
json = "{}"
# create an instance of Details from a JSON string
details_instance = Details.from_json(json)
# print the JSON string representation of the object
print(Details.to_json())

# convert the object into a dict
details_dict = details_instance.to_dict()
# create an instance of Details from a dict
details_from_dict = Details.from_dict(details_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


