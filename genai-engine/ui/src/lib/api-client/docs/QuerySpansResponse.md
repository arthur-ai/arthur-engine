# QuerySpansResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **number** | The total number of spans matching the query parameters | [default to undefined]
**spans** | [**Array&lt;SpanWithMetricsResponse&gt;**](SpanWithMetricsResponse.md) | List of spans with metrics matching the search filters | [default to undefined]

## Example

```typescript
import { QuerySpansResponse } from './api';

const instance: QuerySpansResponse = {
    count,
    spans,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
