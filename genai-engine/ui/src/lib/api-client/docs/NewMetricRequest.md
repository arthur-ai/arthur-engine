# NewMetricRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | [**MetricType**](MetricType.md) | Type of the metric. It can only be one of QueryRelevance, ResponseRelevance, ToolSelection | [default to undefined]
**name** | **string** | Name of metric | [default to undefined]
**metric_metadata** | **string** | Additional metadata for the metric | [default to undefined]
**config** | [**RelevanceMetricConfig**](RelevanceMetricConfig.md) |  | [optional] [default to undefined]

## Example

```typescript
import { NewMetricRequest } from './api';

const instance: NewMetricRequest = {
    type,
    name,
    metric_metadata,
    config,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
