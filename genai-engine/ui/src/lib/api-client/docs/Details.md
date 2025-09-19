# Details

Details of the rule output

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**claims** | [**Array&lt;HallucinationClaimResponse&gt;**](HallucinationClaimResponse.md) |  | [default to undefined]
**pii_entities** | [**Array&lt;PIIEntitySpanResponse&gt;**](PIIEntitySpanResponse.md) |  | [default to undefined]
**toxicity_violation_type** | [**ToxicityViolationType**](ToxicityViolationType.md) |  | [default to undefined]
**score** | **boolean** |  | [optional] [default to undefined]
**message** | **string** |  | [optional] [default to undefined]
**keyword_matches** | [**Array&lt;KeywordSpanResponse&gt;**](KeywordSpanResponse.md) | Each keyword in this list corresponds to a keyword that was both configured in the rule that was run and found in the input text. | [optional] [default to undefined]
**regex_matches** | [**Array&lt;RegexSpanResponse&gt;**](RegexSpanResponse.md) | Each string in this list corresponds to a matching span from the input text that matches the configured regex rule. | [optional] [default to undefined]
**toxicity_score** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { Details } from './api';

const instance: Details = {
    claims,
    pii_entities,
    toxicity_violation_type,
    score,
    message,
    keyword_matches,
    regex_matches,
    toxicity_score,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
