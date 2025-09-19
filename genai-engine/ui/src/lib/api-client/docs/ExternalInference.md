# ExternalInference


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [default to undefined]
**result** | [**RuleResultEnum**](RuleResultEnum.md) |  | [default to undefined]
**created_at** | **number** |  | [default to undefined]
**updated_at** | **number** |  | [default to undefined]
**inference_prompt** | [**ExternalInferencePrompt**](ExternalInferencePrompt.md) |  | [default to undefined]
**inference_feedback** | [**Array&lt;InferenceFeedbackResponse&gt;**](InferenceFeedbackResponse.md) |  | [default to undefined]
**task_id** | **string** |  | [optional] [default to undefined]
**task_name** | **string** |  | [optional] [default to undefined]
**conversation_id** | **string** |  | [optional] [default to undefined]
**inference_response** | [**ExternalInferenceResponse**](ExternalInferenceResponse.md) |  | [optional] [default to undefined]
**user_id** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { ExternalInference } from './api';

const instance: ExternalInference = {
    id,
    result,
    created_at,
    updated_at,
    inference_prompt,
    inference_feedback,
    task_id,
    task_name,
    conversation_id,
    inference_response,
    user_id,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
