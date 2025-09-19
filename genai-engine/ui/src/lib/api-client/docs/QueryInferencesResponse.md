# QueryInferencesResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **number** | The total number of inferences matching the query parameters | [default to undefined]
**inferences** | [**Array&lt;ExternalInference&gt;**](ExternalInference.md) | List of inferences matching the search filters. Length is less than or equal to page_size parameter | [default to undefined]

## Example

```typescript
import { QueryInferencesResponse } from './api';

const instance: QueryInferencesResponse = {
    count,
    inferences,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
