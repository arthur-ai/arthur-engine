# TaskResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  ID of the task | [default to undefined]
**name** | **string** | Name of the task | [default to undefined]
**created_at** | **number** | Time the task was created in unix milliseconds | [default to undefined]
**updated_at** | **number** | Time the task was created in unix milliseconds | [default to undefined]
**rules** | [**Array&lt;RuleResponse&gt;**](RuleResponse.md) | List of all the rules for the task. | [default to undefined]
**is_agentic** | **boolean** |  | [optional] [default to undefined]
**metrics** | [**Array&lt;MetricResponse&gt;**](MetricResponse.md) |  | [optional] [default to undefined]

## Example

```typescript
import { TaskResponse } from './api';

const instance: TaskResponse = {
    id,
    name,
    created_at,
    updated_at,
    rules,
    is_agentic,
    metrics,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
