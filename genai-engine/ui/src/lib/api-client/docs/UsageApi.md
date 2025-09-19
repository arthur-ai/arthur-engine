# UsageApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**getTokenUsageApiV2UsageTokensGet**](#gettokenusageapiv2usagetokensget) | **GET** /api/v2/usage/tokens | Get Token Usage|

# **getTokenUsageApiV2UsageTokensGet**
> Array<TokenUsageResponse> getTokenUsageApiV2UsageTokensGet()

Get token usage.

### Example

```typescript
import {
    UsageApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new UsageApi(configuration);

let startTime: string; //Inclusive start date in ISO8601 string format. Defaults to the beginning of the current day if not provided. (optional) (default to undefined)
let endTime: string; //Exclusive end date in ISO8601 string format. Defaults to the end of the current day if not provided. (optional) (default to undefined)
let groupBy: Array<TokenUsageScope>; //Entities to group token counts on. (optional) (default to undefined)

const { status, data } = await apiInstance.getTokenUsageApiV2UsageTokensGet(
    startTime,
    endTime,
    groupBy
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **startTime** | [**string**] | Inclusive start date in ISO8601 string format. Defaults to the beginning of the current day if not provided. | (optional) defaults to undefined|
| **endTime** | [**string**] | Exclusive end date in ISO8601 string format. Defaults to the end of the current day if not provided. | (optional) defaults to undefined|
| **groupBy** | **Array&lt;TokenUsageScope&gt;** | Entities to group token counts on. | (optional) defaults to undefined|


### Return type

**Array<TokenUsageResponse>**

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

