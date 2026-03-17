# NestedSpanWithMetricsResponse

Nested span response with children for building span trees

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**prompt_token_count** | **int** |  | [optional] 
**completion_token_count** | **int** |  | [optional] 
**total_token_count** | **int** |  | [optional] 
**prompt_token_cost** | **float** |  | [optional] 
**completion_token_cost** | **float** |  | [optional] 
**total_token_cost** | **float** |  | [optional] 
**id** | **str** |  | 
**trace_id** | **str** |  | 
**span_id** | **str** |  | 
**parent_span_id** | **str** |  | [optional] 
**span_kind** | **str** |  | [optional] 
**span_name** | **str** |  | [optional] 
**start_time** | **datetime** |  | 
**end_time** | **datetime** |  | 
**task_id** | **str** |  | [optional] 
**session_id** | **str** |  | [optional] 
**status_code** | **str** | Status code for the span (Unset, Error, Ok) | 
**created_at** | **datetime** |  | 
**updated_at** | **datetime** |  | 
**raw_data** | **object** |  | 
**input_content** | **str** |  | [optional] 
**output_content** | **str** |  | [optional] 
**metric_results** | [**List[MetricResultResponse]**](MetricResultResponse.md) | List of metric results for this span | [optional] [default to []]
**children** | [**List[NestedSpanWithMetricsResponse]**](NestedSpanWithMetricsResponse.md) | Child spans nested under this span | [optional] [default to []]

## Example

```python
from arthur_observability_sdk._generated.models.nested_span_with_metrics_response import NestedSpanWithMetricsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of NestedSpanWithMetricsResponse from a JSON string
nested_span_with_metrics_response_instance = NestedSpanWithMetricsResponse.from_json(json)
# print the JSON string representation of the object
print(NestedSpanWithMetricsResponse.to_json())

# convert the object into a dict
nested_span_with_metrics_response_dict = nested_span_with_metrics_response_instance.to_dict()
# create an instance of NestedSpanWithMetricsResponse from a dict
nested_span_with_metrics_response_from_dict = NestedSpanWithMetricsResponse.from_dict(nested_span_with_metrics_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


