# QuerySpansResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | The total number of spans matching the query parameters | 
**spans** | [**List[SpanWithMetricsResponse]**](SpanWithMetricsResponse.md) | List of spans with metrics matching the search filters | 

## Example

```python
from _generated.models.query_spans_response import QuerySpansResponse

# TODO update the JSON string below
json = "{}"
# create an instance of QuerySpansResponse from a JSON string
query_spans_response_instance = QuerySpansResponse.from_json(json)
# print the JSON string representation of the object
print(QuerySpansResponse.to_json())

# convert the object into a dict
query_spans_response_dict = query_spans_response_instance.to_dict()
# create an instance of QuerySpansResponse from a dict
query_spans_response_from_dict = QuerySpansResponse.from_dict(query_spans_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


