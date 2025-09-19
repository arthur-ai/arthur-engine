# SpanWithMetricsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [default to undefined]
**trace_id** | **string** |  | [default to undefined]
**span_id** | **string** |  | [default to undefined]
**start_time** | **string** |  | [default to undefined]
**end_time** | **string** |  | [default to undefined]
**created_at** | **string** |  | [default to undefined]
**updated_at** | **string** |  | [default to undefined]
**raw_data** | **object** |  | [default to undefined]
**parent_span_id** | **string** |  | [optional] [default to undefined]
**span_kind** | **string** |  | [optional] [default to undefined]
**span_name** | **string** |  | [optional] [default to undefined]
**task_id** | **string** |  | [optional] [default to undefined]
**system_prompt** | **string** |  | [optional] [default to undefined]
**user_query** | **string** |  | [optional] [default to undefined]
**response** | **string** |  | [optional] [default to undefined]
**context** | **Array&lt;object&gt;** |  | [optional] [default to undefined]
**metric_results** | [**Array&lt;MetricResultResponse&gt;**](MetricResultResponse.md) | List of metric results for this span | [optional] [default to undefined]

## Example

```typescript
import { SpanWithMetricsResponse } from './api';

const instance: SpanWithMetricsResponse = {
    id,
    trace_id,
    span_id,
    start_time,
    end_time,
    created_at,
    updated_at,
    raw_data,
    parent_span_id,
    span_kind,
    span_name,
    task_id,
    system_prompt,
    user_query,
    response,
    context,
    metric_results,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
