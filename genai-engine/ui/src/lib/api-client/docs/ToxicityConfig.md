# ToxicityConfig


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**threshold** | **number** | Optional. Float (0, 1) indicating the level of tolerable toxicity to consider the rule passed or failed. Min: 0 (no toxic language) Max: 1 (very toxic language). Default: 0.5 | [optional] [default to 0.5]

## Example

```typescript
import { ToxicityConfig } from './api';

const instance: ToxicityConfig = {
    threshold,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
