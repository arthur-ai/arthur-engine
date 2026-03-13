# PIIEntitySpanResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**entity** | [**PIIEntityTypes**](PIIEntityTypes.md) |  | 
**span** | **str** | The subtext within the input string that was identified as PII. | 
**confidence** | **float** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.pii_entity_span_response import PIIEntitySpanResponse

# TODO update the JSON string below
json = "{}"
# create an instance of PIIEntitySpanResponse from a JSON string
pii_entity_span_response_instance = PIIEntitySpanResponse.from_json(json)
# print the JSON string representation of the object
print(PIIEntitySpanResponse.to_json())

# convert the object into a dict
pii_entity_span_response_dict = pii_entity_span_response_instance.to_dict()
# create an instance of PIIEntitySpanResponse from a dict
pii_entity_span_response_from_dict = PIIEntitySpanResponse.from_dict(pii_entity_span_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


