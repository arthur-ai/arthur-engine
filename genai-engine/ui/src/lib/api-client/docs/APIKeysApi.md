# APIKeysApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**createApiKeyAuthApiKeysPost**](#createapikeyauthapikeyspost) | **POST** /auth/api_keys/ | Create Api Key|
|[**deactivateApiKeyAuthApiKeysDeactivateApiKeyIdDelete**](#deactivateapikeyauthapikeysdeactivateapikeyiddelete) | **DELETE** /auth/api_keys/deactivate/{api_key_id} | Deactivate Api Key|
|[**getAllActiveApiKeysAuthApiKeysGet**](#getallactiveapikeysauthapikeysget) | **GET** /auth/api_keys/ | Get All Active Api Keys|
|[**getApiKeyAuthApiKeysApiKeyIdGet**](#getapikeyauthapikeysapikeyidget) | **GET** /auth/api_keys/{api_key_id} | Get Api Key|

# **createApiKeyAuthApiKeysPost**
> ApiKeyResponse createApiKeyAuthApiKeysPost(newApiKeyRequest)

Generates a new API key. Up to 1000 active keys can exist at the same time by default. Contact your system administrator if you need more. Allowed roles are: DEFAULT-RULE-ADMIN, TASK-ADMIN, VALIDATION-USER, ORG-AUDITOR, ORG-ADMIN.

### Example

```typescript
import {
    APIKeysApi,
    Configuration,
    NewApiKeyRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new APIKeysApi(configuration);

let newApiKeyRequest: NewApiKeyRequest; //

const { status, data } = await apiInstance.createApiKeyAuthApiKeysPost(
    newApiKeyRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **newApiKeyRequest** | **NewApiKeyRequest**|  | |


### Return type

**ApiKeyResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **deactivateApiKeyAuthApiKeysDeactivateApiKeyIdDelete**
> ApiKeyResponse deactivateApiKeyAuthApiKeysDeactivateApiKeyIdDelete()


### Example

```typescript
import {
    APIKeysApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new APIKeysApi(configuration);

let apiKeyId: string; // (default to undefined)

const { status, data } = await apiInstance.deactivateApiKeyAuthApiKeysDeactivateApiKeyIdDelete(
    apiKeyId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiKeyId** | [**string**] |  | defaults to undefined|


### Return type

**ApiKeyResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getAllActiveApiKeysAuthApiKeysGet**
> Array<ApiKeyResponse> getAllActiveApiKeysAuthApiKeysGet()


### Example

```typescript
import {
    APIKeysApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new APIKeysApi(configuration);

const { status, data } = await apiInstance.getAllActiveApiKeysAuthApiKeysGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**Array<ApiKeyResponse>**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getApiKeyAuthApiKeysApiKeyIdGet**
> ApiKeyResponse getApiKeyAuthApiKeysApiKeyIdGet()


### Example

```typescript
import {
    APIKeysApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new APIKeysApi(configuration);

let apiKeyId: string; // (default to undefined)

const { status, data } = await apiInstance.getApiKeyAuthApiKeysApiKeyIdGet(
    apiKeyId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiKeyId** | [**string**] |  | defaults to undefined|


### Return type

**ApiKeyResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

