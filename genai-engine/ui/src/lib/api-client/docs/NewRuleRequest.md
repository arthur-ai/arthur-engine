# NewRuleRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** | Name of the rule | [default to undefined]
**type** | **string** | Type of the rule. It can only be one of KeywordRule, RegexRule, ModelSensitiveDataRule, ModelHallucinationRule, ModelHallucinationRuleV2, PromptInjectionRule, PIIDataRule | [default to undefined]
**apply_to_prompt** | **boolean** | Boolean value to enable or disable the rule for llm prompt | [default to undefined]
**apply_to_response** | **boolean** | Boolean value to enable or disable the rule for llm response | [default to undefined]
**config** | [**Config**](Config.md) |  | [optional] [default to undefined]

## Example

```typescript
import { NewRuleRequest } from './api';

const instance: NewRuleRequest = {
    name,
    type,
    apply_to_prompt,
    apply_to_response,
    config,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
