# MetricResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | ID of the Metric | [default to undefined]
**name** | **string** | Name of the Metric | [default to undefined]
**type** | [**MetricType**](MetricType.md) | Type of the Metric | [default to undefined]
**metric_metadata** | **string** | Metadata of the Metric | [default to undefined]
**created_at** | **string** | Time the Metric was created in unix milliseconds | [default to undefined]
**updated_at** | **string** | Time the Metric was updated in unix milliseconds | [default to undefined]
**config** | **string** |  | [optional] [default to undefined]
**enabled** | **boolean** |  | [optional] [default to undefined]

## Example

```typescript
import { MetricResponse } from './api';

const instance: MetricResponse = {
    id,
    name,
    type,
    metric_metadata,
    created_at,
    updated_at,
    config,
    enabled,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
