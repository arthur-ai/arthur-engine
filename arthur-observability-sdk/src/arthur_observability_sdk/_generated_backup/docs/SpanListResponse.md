# SpanListResponse

Response for span list endpoint

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | Total number of spans matching filters | 
**spans** | [**List[SpanMetadataResponse]**](SpanMetadataResponse.md) | List of span metadata | 

## Example

```python
from _generated.models.span_list_response import SpanListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SpanListResponse from a JSON string
span_list_response_instance = SpanListResponse.from_json(json)
# print the JSON string representation of the object
print(SpanListResponse.to_json())

# convert the object into a dict
span_list_response_dict = span_list_response_instance.to_dict()
# create an instance of SpanListResponse from a dict
span_list_response_from_dict = SpanListResponse.from_dict(span_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


