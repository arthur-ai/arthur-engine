# CreateUserRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**email** | **string** |  | [default to undefined]
**password** | **string** |  | [default to undefined]
**roles** | **Array&lt;string&gt;** |  | [default to undefined]
**firstName** | **string** |  | [default to undefined]
**lastName** | **string** |  | [default to undefined]
**temporary** | **boolean** |  | [optional] [default to true]

## Example

```typescript
import { CreateUserRequest } from './api';

const instance: CreateUserRequest = {
    email,
    password,
    roles,
    firstName,
    lastName,
    temporary,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
