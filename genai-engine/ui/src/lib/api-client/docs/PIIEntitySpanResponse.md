# PIIEntitySpanResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**entity** | [**PIIEntityTypes**](PIIEntityTypes.md) |  | [default to undefined]
**span** | **string** | The subtext within the input string that was identified as PII. | [default to undefined]
**confidence** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { PIIEntitySpanResponse } from './api';

const instance: PIIEntitySpanResponse = {
    entity,
    span,
    confidence,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
