# QueryTracesWithMetricsResponse

New response format that groups spans into traces with nested structure

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | The total number of spans matching the query parameters | 
**traces** | [**List[TraceResponse]**](TraceResponse.md) | List of traces containing nested spans matching the search filters | 

## Example

```python
from arthur_observability_sdk._generated.models.query_traces_with_metrics_response import QueryTracesWithMetricsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of QueryTracesWithMetricsResponse from a JSON string
query_traces_with_metrics_response_instance = QueryTracesWithMetricsResponse.from_json(json)
# print the JSON string representation of the object
print(QueryTracesWithMetricsResponse.to_json())

# convert the object into a dict
query_traces_with_metrics_response_dict = query_traces_with_metrics_response_instance.to_dict()
# create an instance of QueryTracesWithMetricsResponse from a dict
query_traces_with_metrics_response_from_dict = QueryTracesWithMetricsResponse.from_dict(query_traces_with_metrics_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


