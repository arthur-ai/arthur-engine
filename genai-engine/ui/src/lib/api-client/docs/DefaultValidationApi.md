# DefaultValidationApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**defaultValidatePromptApiV2ValidatePromptPost**](#defaultvalidatepromptapiv2validatepromptpost) | **POST** /api/v2/validate_prompt | Default Validate Prompt|
|[**defaultValidateResponseApiV2ValidateResponseInferenceIdPost**](#defaultvalidateresponseapiv2validateresponseinferenceidpost) | **POST** /api/v2/validate_response/{inference_id} | Default Validate Response|

# **defaultValidatePromptApiV2ValidatePromptPost**
> ValidationResult defaultValidatePromptApiV2ValidatePromptPost(promptValidationRequest)

[Deprecated] Validate a non-task related prompt based on the configured default rules.

### Example

```typescript
import {
    DefaultValidationApi,
    Configuration,
    PromptValidationRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultValidationApi(configuration);

let promptValidationRequest: PromptValidationRequest; //

const { status, data } = await apiInstance.defaultValidatePromptApiV2ValidatePromptPost(
    promptValidationRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **promptValidationRequest** | **PromptValidationRequest**|  | |


### Return type

**ValidationResult**

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

# **defaultValidateResponseApiV2ValidateResponseInferenceIdPost**
> ValidationResult defaultValidateResponseApiV2ValidateResponseInferenceIdPost(responseValidationRequest, )

[Deprecated] Validate a non-task related generated response based on the configured default rules. Inference ID corresponds to the previously validated associated prompt’s inference ID. Must provide context if a Hallucination Rule is an enabled default rule.

### Example

```typescript
import {
    DefaultValidationApi,
    Configuration,
    ResponseValidationRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultValidationApi(configuration);

let responseValidationRequest: ResponseValidationRequest; //
let inferenceId: string; // (default to undefined)

const { status, data } = await apiInstance.defaultValidateResponseApiV2ValidateResponseInferenceIdPost(
    responseValidationRequest,
    inferenceId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **responseValidationRequest** | **ResponseValidationRequest**|  | |
| **inferenceId** | [**string**] |  | defaults to undefined|


### Return type

**ValidationResult**

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

