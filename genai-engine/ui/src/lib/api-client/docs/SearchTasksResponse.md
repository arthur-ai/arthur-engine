# SearchTasksResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **number** | The total number of tasks matching the parameters | [default to undefined]
**tasks** | [**Array&lt;TaskResponse&gt;**](TaskResponse.md) | List of tasks matching the search filters. Length is less than or equal to page_size parameter | [default to undefined]

## Example

```typescript
import { SearchTasksResponse } from './api';

const instance: SearchTasksResponse = {
    count,
    tasks,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
