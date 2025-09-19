# SearchRulesRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**rule_ids** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**rule_scopes** | [**Array&lt;RuleScope&gt;**](RuleScope.md) |  | [optional] [default to undefined]
**prompt_enabled** | **boolean** |  | [optional] [default to undefined]
**response_enabled** | **boolean** |  | [optional] [default to undefined]
**rule_types** | [**Array&lt;RuleType&gt;**](RuleType.md) |  | [optional] [default to undefined]

## Example

```typescript
import { SearchRulesRequest } from './api';

const instance: SearchRulesRequest = {
    rule_ids,
    rule_scopes,
    prompt_enabled,
    response_enabled,
    rule_types,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
