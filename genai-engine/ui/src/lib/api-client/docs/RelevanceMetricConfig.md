# RelevanceMetricConfig

Configuration for relevance metrics including QueryRelevance and ResponseRelevance

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**relevance_threshold** | **number** |  | [optional] [default to undefined]
**use_llm_judge** | **boolean** | Whether to use LLM as a judge for relevance scoring | [optional] [default to true]

## Example

```typescript
import { RelevanceMetricConfig } from './api';

const instance: RelevanceMetricConfig = {
    relevance_threshold,
    use_llm_judge,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
