# ExternalInferenceResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [default to undefined]
**inference_id** | **string** |  | [default to undefined]
**result** | [**RuleResultEnum**](RuleResultEnum.md) |  | [default to undefined]
**created_at** | **number** |  | [default to undefined]
**updated_at** | **number** |  | [default to undefined]
**message** | **string** |  | [default to undefined]
**response_rule_results** | [**Array&lt;ExternalRuleResult&gt;**](ExternalRuleResult.md) |  | [default to undefined]
**context** | **string** |  | [optional] [default to undefined]
**tokens** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { ExternalInferenceResponse } from './api';

const instance: ExternalInferenceResponse = {
    id,
    inference_id,
    result,
    created_at,
    updated_at,
    message,
    response_rule_results,
    context,
    tokens,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
