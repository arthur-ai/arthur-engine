# InferenceFeedbackResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [default to undefined]
**inference_id** | **string** |  | [default to undefined]
**target** | [**InferenceFeedbackTarget**](InferenceFeedbackTarget.md) |  | [default to undefined]
**score** | **number** |  | [default to undefined]
**created_at** | **string** |  | [default to undefined]
**updated_at** | **string** |  | [default to undefined]
**reason** | **string** |  | [optional] [default to undefined]
**user_id** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { InferenceFeedbackResponse } from './api';

const instance: InferenceFeedbackResponse = {
    id,
    inference_id,
    target,
    score,
    created_at,
    updated_at,
    reason,
    user_id,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
