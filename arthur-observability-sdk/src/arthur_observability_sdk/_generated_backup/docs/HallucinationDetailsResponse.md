# HallucinationDetailsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**score** | **bool** |  | [optional] 
**message** | **str** |  | [optional] 
**claims** | [**List[HallucinationClaimResponse]**](HallucinationClaimResponse.md) |  | 

## Example

```python
from _generated.models.hallucination_details_response import HallucinationDetailsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of HallucinationDetailsResponse from a JSON string
hallucination_details_response_instance = HallucinationDetailsResponse.from_json(json)
# print the JSON string representation of the object
print(HallucinationDetailsResponse.to_json())

# convert the object into a dict
hallucination_details_response_dict = hallucination_details_response_instance.to_dict()
# create an instance of HallucinationDetailsResponse from a dict
hallucination_details_response_from_dict = HallucinationDetailsResponse.from_dict(hallucination_details_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


