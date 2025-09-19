# MetricResultResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | ID of the metric result | [default to undefined]
**metric_type** | [**MetricType**](MetricType.md) | Type of the metric | [default to undefined]
**prompt_tokens** | **number** | Number of prompt tokens used | [default to undefined]
**completion_tokens** | **number** | Number of completion tokens used | [default to undefined]
**latency_ms** | **number** | Latency in milliseconds | [default to undefined]
**span_id** | **string** | ID of the span this result belongs to | [default to undefined]
**metric_id** | **string** | ID of the metric that generated this result | [default to undefined]
**created_at** | **string** | Time the result was created | [default to undefined]
**updated_at** | **string** | Time the result was last updated | [default to undefined]
**details** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { MetricResultResponse } from './api';

const instance: MetricResultResponse = {
    id,
    metric_type,
    prompt_tokens,
    completion_tokens,
    latency_ms,
    span_id,
    metric_id,
    created_at,
    updated_at,
    details,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
