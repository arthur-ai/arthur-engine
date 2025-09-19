# RuleResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | ID of the Rule | [default to undefined]
**name** | **string** | Name of the Rule | [default to undefined]
**type** | [**RuleType**](RuleType.md) | Type of Rule | [default to undefined]
**apply_to_prompt** | **boolean** | Rule applies to prompt | [default to undefined]
**apply_to_response** | **boolean** | Rule applies to response | [default to undefined]
**scope** | [**RuleScope**](RuleScope.md) | Scope of the rule. The rule can be set at default level or task level. | [default to undefined]
**created_at** | **number** | Time the rule was created in unix milliseconds | [default to undefined]
**updated_at** | **number** | Time the rule was updated in unix milliseconds | [default to undefined]
**enabled** | **boolean** |  | [optional] [default to undefined]
**config** | [**Config1**](Config1.md) |  | [optional] [default to undefined]

## Example

```typescript
import { RuleResponse } from './api';

const instance: RuleResponse = {
    id,
    name,
    type,
    apply_to_prompt,
    apply_to_response,
    scope,
    created_at,
    updated_at,
    enabled,
    config,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
