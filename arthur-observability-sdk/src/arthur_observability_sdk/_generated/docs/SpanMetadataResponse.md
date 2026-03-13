# SpanMetadataResponse

Lightweight span metadata for list operations

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**prompt_token_count** | **int** |  | [optional] 
**completion_token_count** | **int** |  | [optional] 
**total_token_count** | **int** |  | [optional] 
**prompt_token_cost** | **float** |  | [optional] 
**completion_token_cost** | **float** |  | [optional] 
**total_token_cost** | **float** |  | [optional] 
**id** | **str** | Internal database ID | 
**trace_id** | **str** | ID of the parent trace | 
**span_id** | **str** | OpenTelemetry span ID | 
**parent_span_id** | **str** |  | [optional] 
**span_kind** | **str** |  | [optional] 
**span_name** | **str** |  | [optional] 
**start_time** | **datetime** | Span start time | 
**end_time** | **datetime** | Span end time | 
**duration_ms** | **float** | Span duration in milliseconds | 
**task_id** | **str** |  | [optional] 
**user_id** | **str** |  | [optional] 
**session_id** | **str** |  | [optional] 
**status_code** | **str** | Status code (Unset, Error, Ok) | 
**created_at** | **datetime** | When the span was created | 
**updated_at** | **datetime** | When the span was updated | 
**input_content** | **str** |  | [optional] 
**output_content** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.span_metadata_response import SpanMetadataResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SpanMetadataResponse from a JSON string
span_metadata_response_instance = SpanMetadataResponse.from_json(json)
# print the JSON string representation of the object
print(SpanMetadataResponse.to_json())

# convert the object into a dict
span_metadata_response_dict = span_metadata_response_instance.to_dict()
# create an instance of SpanMetadataResponse from a dict
span_metadata_response_from_dict = SpanMetadataResponse.from_dict(span_metadata_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


