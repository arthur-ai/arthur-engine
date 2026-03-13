# HallucinationClaimResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**claim** | **str** |  | 
**valid** | **bool** |  | 
**reason** | **str** |  | 
**order_number** | **int** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.hallucination_claim_response import HallucinationClaimResponse

# TODO update the JSON string below
json = "{}"
# create an instance of HallucinationClaimResponse from a JSON string
hallucination_claim_response_instance = HallucinationClaimResponse.from_json(json)
# print the JSON string representation of the object
print(HallucinationClaimResponse.to_json())

# convert the object into a dict
hallucination_claim_response_dict = hallucination_claim_response_instance.to_dict()
# create an instance of HallucinationClaimResponse from a dict
hallucination_claim_response_from_dict = HallucinationClaimResponse.from_dict(hallucination_claim_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


