# TaskBasedValidationApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**validatePromptEndpointApiV2TasksTaskIdValidatePromptPost**](#validatepromptendpointapiv2taskstaskidvalidatepromptpost) | **POST** /api/v2/tasks/{task_id}/validate_prompt | Validate Prompt Endpoint|
|[**validateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPost**](#validateresponseendpointapiv2taskstaskidvalidateresponseinferenceidpost) | **POST** /api/v2/tasks/{task_id}/validate_response/{inference_id} | Validate Response Endpoint|

# **validatePromptEndpointApiV2TasksTaskIdValidatePromptPost**
> ValidationResult validatePromptEndpointApiV2TasksTaskIdValidatePromptPost(promptValidationRequest, )

Validate a prompt based on the configured rules for this task. Note: Rules related to specific tasks are cached for 60 seconds.

### Example

```typescript
import {
    TaskBasedValidationApi,
    Configuration,
    PromptValidationRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TaskBasedValidationApi(configuration);

let promptValidationRequest: PromptValidationRequest; //
let taskId: string; // (default to undefined)

const { status, data } = await apiInstance.validatePromptEndpointApiV2TasksTaskIdValidatePromptPost(
    promptValidationRequest,
    taskId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **promptValidationRequest** | **PromptValidationRequest**|  | |
| **taskId** | [**string**] |  | defaults to undefined|


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
|**400** | Bad Request |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **validateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPost**
> ValidationResult validateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPost(responseValidationRequest, )

Validate a response based on the configured rules for this task. Inference ID corresponds to the previously validated associated prompt’s inference id. Must provide context if a Hallucination Rule is an enabled task rule. Note: Rules related to specific tasks are cached for 60 seconds.

### Example

```typescript
import {
    TaskBasedValidationApi,
    Configuration,
    ResponseValidationRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TaskBasedValidationApi(configuration);

let responseValidationRequest: ResponseValidationRequest; //
let inferenceId: string; // (default to undefined)
let taskId: string; // (default to undefined)

const { status, data } = await apiInstance.validateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPost(
    responseValidationRequest,
    inferenceId,
    taskId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **responseValidationRequest** | **ResponseValidationRequest**|  | |
| **inferenceId** | [**string**] |  | defaults to undefined|
| **taskId** | [**string**] |  | defaults to undefined|


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
|**400** | Bad Request |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

