# Config1

Config of the rule

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**keywords** | **Array&lt;string&gt;** | List of Keywords | [default to undefined]
**regex_patterns** | **Array&lt;string&gt;** | List of Regex patterns to be used for validation. Be sure to encode requests in JSON and account for escape characters. | [default to undefined]
**examples** | [**Array&lt;ExampleConfig&gt;**](ExampleConfig.md) | List of all the examples for Sensitive Data Rule | [default to undefined]
**hint** | **string** |  | [optional] [default to undefined]
**threshold** | **number** | Optional. Float (0, 1) indicating the level of tolerable toxicity to consider the rule passed or failed. Min: 0 (no toxic language) Max: 1 (very toxic language). Default: 0.5 | [optional] [default to 0.5]
**disabled_pii_entities** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**confidence_threshold** | **number** |  | [optional] [default to undefined]
**allow_list** | **Array&lt;string&gt;** |  | [optional] [default to undefined]

## Example

```typescript
import { Config1 } from './api';

const instance: Config1 = {
    keywords,
    regex_patterns,
    examples,
    hint,
    threshold,
    disabled_pii_entities,
    confidence_threshold,
    allow_list,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
