# TracesApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**receiveTracesV1TracesPost**](#receivetracesv1tracespost) | **POST** /v1/traces | Receive Traces|

# **receiveTracesV1TracesPost**
> any receiveTracesV1TracesPost(body)

Receiver for OpenInference trace standard.

### Example

```typescript
import {
    TracesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new TracesApi(configuration);

let body: File; //

const { status, data } = await apiInstance.receiveTracesV1TracesPost(
    body
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **body** | **File**|  | |


### Return type

**any**

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

