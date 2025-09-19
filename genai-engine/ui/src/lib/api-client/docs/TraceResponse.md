# TraceResponse

Response model for a single trace containing nested spans

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**trace_id** | **string** | ID of the trace | [default to undefined]
**start_time** | **string** | Start time of the earliest span in this trace | [default to undefined]
**end_time** | **string** | End time of the latest span in this trace | [default to undefined]
**root_spans** | [**Array&lt;NestedSpanWithMetricsResponse&gt;**](NestedSpanWithMetricsResponse.md) | Root spans (spans with no parent) in this trace, with children nested | [optional] [default to undefined]

## Example

```typescript
import { TraceResponse } from './api';

const instance: TraceResponse = {
    trace_id,
    start_time,
    end_time,
    root_spans,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
