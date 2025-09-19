# SearchRulesResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **number** | The total number of rules matching the parameters | [default to undefined]
**rules** | [**Array&lt;RuleResponse&gt;**](RuleResponse.md) | List of rules matching the search filters. Length is less than or equal to page_size parameter | [default to undefined]

## Example

```typescript
import { SearchRulesResponse } from './api';

const instance: SearchRulesResponse = {
    count,
    rules,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
