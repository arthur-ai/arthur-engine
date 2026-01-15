# UnregisteredRootSpansResponse

Response for unregistered root spans endpoint

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**groups** | [**List[UnregisteredRootSpanGroup]**](UnregisteredRootSpanGroup.md) | List of grouped root spans, ordered by count descending | 
**total_count** | **int** | Total number of root spans (and traces) across all groups | 

## Example

```python
from arthur_observability_sdk._generated.models.unregistered_root_spans_response import UnregisteredRootSpansResponse

# TODO update the JSON string below
json = "{}"
# create an instance of UnregisteredRootSpansResponse from a JSON string
unregistered_root_spans_response_instance = UnregisteredRootSpansResponse.from_json(json)
# print the JSON string representation of the object
print(UnregisteredRootSpansResponse.to_json())

# convert the object into a dict
unregistered_root_spans_response_dict = unregistered_root_spans_response_instance.to_dict()
# create an instance of UnregisteredRootSpansResponse from a dict
unregistered_root_spans_response_from_dict = UnregisteredRootSpansResponse.from_dict(unregistered_root_spans_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


