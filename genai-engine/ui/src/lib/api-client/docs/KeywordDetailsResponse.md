# KeywordDetailsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**score** | **boolean** |  | [optional] [default to undefined]
**message** | **string** |  | [optional] [default to undefined]
**keyword_matches** | [**Array&lt;KeywordSpanResponse&gt;**](KeywordSpanResponse.md) | Each keyword in this list corresponds to a keyword that was both configured in the rule that was run and found in the input text. | [optional] [default to undefined]

## Example

```typescript
import { KeywordDetailsResponse } from './api';

const instance: KeywordDetailsResponse = {
    score,
    message,
    keyword_matches,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
