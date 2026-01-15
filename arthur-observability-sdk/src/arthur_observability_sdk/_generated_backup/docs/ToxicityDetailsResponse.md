# ToxicityDetailsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**score** | **bool** |  | [optional] 
**message** | **str** |  | [optional] 
**toxicity_score** | **float** |  | [optional] 
**toxicity_violation_type** | [**ToxicityViolationType**](ToxicityViolationType.md) |  | 

## Example

```python
from _generated.models.toxicity_details_response import ToxicityDetailsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ToxicityDetailsResponse from a JSON string
toxicity_details_response_instance = ToxicityDetailsResponse.from_json(json)
# print the JSON string representation of the object
print(ToxicityDetailsResponse.to_json())

# convert the object into a dict
toxicity_details_response_dict = toxicity_details_response_instance.to_dict()
# create an instance of ToxicityDetailsResponse from a dict
toxicity_details_response_from_dict = ToxicityDetailsResponse.from_dict(toxicity_details_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


