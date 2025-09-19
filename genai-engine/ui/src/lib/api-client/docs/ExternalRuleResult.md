# ExternalRuleResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  ID of the rule | [default to undefined]
**name** | **string** | Name of the rule | [default to undefined]
**rule_type** | [**RuleType**](RuleType.md) | Type of the rule | [default to undefined]
**scope** | [**RuleScope**](RuleScope.md) | Scope of the rule. The rule can be set at default level or task level. | [default to undefined]
**result** | [**RuleResultEnum**](RuleResultEnum.md) | Result if the rule | [default to undefined]
**latency_ms** | **number** | Duration in millisesconds of rule execution | [default to undefined]
**details** | [**Details**](Details.md) |  | [optional] [default to undefined]

## Example

```typescript
import { ExternalRuleResult } from './api';

const instance: ExternalRuleResult = {
    id,
    name,
    rule_type,
    scope,
    result,
    latency_ms,
    details,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
