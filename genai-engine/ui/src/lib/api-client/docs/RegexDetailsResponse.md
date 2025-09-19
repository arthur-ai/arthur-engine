# RegexDetailsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**score** | **boolean** |  | [optional] [default to undefined]
**message** | **string** |  | [optional] [default to undefined]
**regex_matches** | [**Array&lt;RegexSpanResponse&gt;**](RegexSpanResponse.md) | Each string in this list corresponds to a matching span from the input text that matches the configured regex rule. | [optional] [default to undefined]

## Example

```typescript
import { RegexDetailsResponse } from './api';

const instance: RegexDetailsResponse = {
    score,
    message,
    regex_matches,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
