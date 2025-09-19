# ChatRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**user_prompt** | **string** | Prompt user wants to send to chat. | [default to undefined]
**conversation_id** | **string** | Conversation ID | [default to undefined]
**file_ids** | **Array&lt;string&gt;** | list of file IDs to retrieve from during chat. | [default to undefined]

## Example

```typescript
import { ChatRequest } from './api';

const instance: ChatRequest = {
    user_prompt,
    conversation_id,
    file_ids,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
