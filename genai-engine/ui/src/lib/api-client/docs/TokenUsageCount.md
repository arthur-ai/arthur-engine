# TokenUsageCount


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**inference** | **number** | Number of inference tokens sent to Arthur. | [default to undefined]
**eval_prompt** | **number** | Number of Prompt tokens incurred by Arthur rules. | [default to undefined]
**eval_completion** | **number** | Number of Completion tokens incurred by Arthur rules. | [default to undefined]
**user_input** | **number** | Number of user input tokens sent to Arthur. This field is deprecated and will be removed in the future. Use inference instead. | [default to undefined]
**prompt** | **number** | Number of Prompt tokens incurred by Arthur rules. This field is deprecated and will be removed in the future. Use eval_prompt instead. | [default to undefined]
**completion** | **number** | Number of Completion tokens incurred by Arthur rules. This field is deprecated and will be removed in the future. Use eval_completion instead. | [default to undefined]

## Example

```typescript
import { TokenUsageCount } from './api';

const instance: TokenUsageCount = {
    inference,
    eval_prompt,
    eval_completion,
    user_input,
    prompt,
    completion,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
