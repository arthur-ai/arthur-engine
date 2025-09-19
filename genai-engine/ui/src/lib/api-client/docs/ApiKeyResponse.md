# ApiKeyResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | ID of the key | [default to undefined]
**is_active** | **boolean** | Status of the key. | [default to undefined]
**created_at** | **string** | Creation time of the key | [default to undefined]
**key** | **string** |  | [optional] [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**deactivated_at** | **string** |  | [optional] [default to undefined]
**message** | **string** |  | [optional] [default to undefined]
**roles** | **Array&lt;string&gt;** | Roles of the API key | [optional] [default to undefined]

## Example

```typescript
import { ApiKeyResponse } from './api';

const instance: ApiKeyResponse = {
    id,
    is_active,
    created_at,
    key,
    description,
    deactivated_at,
    message,
    roles,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
