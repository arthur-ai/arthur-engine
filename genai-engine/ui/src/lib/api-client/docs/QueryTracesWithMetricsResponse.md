# QueryTracesWithMetricsResponse

New response format that groups spans into traces with nested structure

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **number** | The total number of spans matching the query parameters | [default to undefined]
**traces** | [**Array&lt;TraceResponse&gt;**](TraceResponse.md) | List of traces containing nested spans matching the search filters | [default to undefined]

## Example

```typescript
import { QueryTracesWithMetricsResponse } from './api';

const instance: QueryTracesWithMetricsResponse = {
    count,
    traces,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
