# ChatResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**inference_id** | **string** | ID of the inference sent to the chat | [default to undefined]
**conversation_id** | **string** | ID of the conversation session | [default to undefined]
**timestamp** | **number** | Time the inference was made in unix milliseconds | [default to undefined]
**retrieved_context** | [**Array&lt;ChatDocumentContext&gt;**](ChatDocumentContext.md) | related sections of documents that were most relevant to the inference prompt. Formatted as a list of retrieved context chunks which include document name, seq num, and context. | [default to undefined]
**llm_response** | **string** | response from the LLM for the original user prompt | [default to undefined]
**prompt_results** | [**Array&lt;ExternalRuleResult&gt;**](ExternalRuleResult.md) | list of rule results for the user prompt | [default to undefined]
**response_results** | [**Array&lt;ExternalRuleResult&gt;**](ExternalRuleResult.md) | list of rule results for the llm response | [default to undefined]

## Example

```typescript
import { ChatResponse } from './api';

const instance: ChatResponse = {
    inference_id,
    conversation_id,
    timestamp,
    retrieved_context,
    llm_response,
    prompt_results,
    response_results,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
