# PIIDetailsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**score** | **bool** |  | [optional] 
**message** | **str** |  | [optional] 
**pii_entities** | [**List[PIIEntitySpanResponse]**](PIIEntitySpanResponse.md) |  | 

## Example

```python
from _generated.models.pii_details_response import PIIDetailsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of PIIDetailsResponse from a JSON string
pii_details_response_instance = PIIDetailsResponse.from_json(json)
# print the JSON string representation of the object
print(PIIDetailsResponse.to_json())

# convert the object into a dict
pii_details_response_dict = pii_details_response_instance.to_dict()
# create an instance of PIIDetailsResponse from a dict
pii_details_response_from_dict = PIIDetailsResponse.from_dict(pii_details_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


