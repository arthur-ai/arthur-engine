# ChatApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**chatRequest**](#chatrequest) | **POST** /api/chat/ | Chat|
|[**deleteFileApiChatFilesFileIdDelete**](#deletefileapichatfilesfileiddelete) | **DELETE** /api/chat/files/{file_id} | Delete File|
|[**getConversationsApiChatConversationsGet**](#getconversationsapichatconversationsget) | **GET** /api/chat/conversations | Get Conversations|
|[**getDefaultTaskApiChatDefaultTaskGet**](#getdefaulttaskapichatdefaulttaskget) | **GET** /api/chat/default_task | Get Default Task|
|[**getFilesApiChatFilesGet**](#getfilesapichatfilesget) | **GET** /api/chat/files | Get Files|
|[**getInferenceDocumentContextApiChatContextInferenceIdGet**](#getinferencedocumentcontextapichatcontextinferenceidget) | **GET** /api/chat/context/{inference_id} | Get Inference Document Context|
|[**postChatFeedbackApiChatFeedbackInferenceIdPost**](#postchatfeedbackapichatfeedbackinferenceidpost) | **POST** /api/chat/feedback/{inference_id} | Post Chat Feedback|
|[**postChatFeedbackApiChatFeedbackInferenceIdPost_0**](#postchatfeedbackapichatfeedbackinferenceidpost_0) | **POST** /api/chat/feedback/{inference_id} | Post Chat Feedback|
|[**updateDefaultTaskApiChatDefaultTaskPut**](#updatedefaulttaskapichatdefaulttaskput) | **PUT** /api/chat/default_task | Update Default Task|
|[**uploadEmbeddingsFileApiChatFilesPost**](#uploadembeddingsfileapichatfilespost) | **POST** /api/chat/files | Upload Embeddings File|

# **chatRequest**
> ChatResponse chatRequest(chatRequest)

Chat request for Arthur Chat

### Example

```typescript
import {
    ChatApi,
    Configuration,
    ChatRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ChatApi(configuration);

let chatRequest: ChatRequest; //

const { status, data } = await apiInstance.chatRequest(
    chatRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **chatRequest** | **ChatRequest**|  | |


### Return type

**ChatResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **deleteFileApiChatFilesFileIdDelete**
> any deleteFileApiChatFilesFileIdDelete()

Remove a file by ID. This action cannot be undone.

### Example

```typescript
import {
    ChatApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ChatApi(configuration);

let fileId: string; // (default to undefined)

const { status, data } = await apiInstance.deleteFileApiChatFilesFileIdDelete(
    fileId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fileId** | [**string**] |  | defaults to undefined|


### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getConversationsApiChatConversationsGet**
> PageListConversationBaseResponse getConversationsApiChatConversationsGet()

Get list of conversation IDs.

### Example

```typescript
import {
    ChatApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ChatApi(configuration);

let page: number; // (optional) (default to 1)
let size: number; // (optional) (default to 50)

const { status, data } = await apiInstance.getConversationsApiChatConversationsGet(
    page,
    size
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **page** | [**number**] |  | (optional) defaults to 1|
| **size** | [**number**] |  | (optional) defaults to 50|


### Return type

**PageListConversationBaseResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getDefaultTaskApiChatDefaultTaskGet**
> ChatDefaultTaskResponse getDefaultTaskApiChatDefaultTaskGet()

Get the default task for Arthur Chat.

### Example

```typescript
import {
    ChatApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ChatApi(configuration);

const { status, data } = await apiInstance.getDefaultTaskApiChatDefaultTaskGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**ChatDefaultTaskResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getFilesApiChatFilesGet**
> Array<ExternalDocument> getFilesApiChatFilesGet()

List uploaded files. Only files that are global or owned by the caller are returned.

### Example

```typescript
import {
    ChatApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ChatApi(configuration);

const { status, data } = await apiInstance.getFilesApiChatFilesGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**Array<ExternalDocument>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getInferenceDocumentContextApiChatContextInferenceIdGet**
> Array<ChatDocumentContext> getInferenceDocumentContextApiChatContextInferenceIdGet()

Get document context used for a past inference ID.

### Example

```typescript
import {
    ChatApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ChatApi(configuration);

let inferenceId: string; // (default to undefined)

const { status, data } = await apiInstance.getInferenceDocumentContextApiChatContextInferenceIdGet(
    inferenceId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **inferenceId** | [**string**] |  | defaults to undefined|


### Return type

**Array<ChatDocumentContext>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **postChatFeedbackApiChatFeedbackInferenceIdPost**
> any postChatFeedbackApiChatFeedbackInferenceIdPost(feedbackRequest, )

Post feedback for Arthur Chat.

### Example

```typescript
import {
    ChatApi,
    Configuration,
    FeedbackRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ChatApi(configuration);

let feedbackRequest: FeedbackRequest; //
let inferenceId: string; // (default to undefined)

const { status, data } = await apiInstance.postChatFeedbackApiChatFeedbackInferenceIdPost(
    feedbackRequest,
    inferenceId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **feedbackRequest** | **FeedbackRequest**|  | |
| **inferenceId** | [**string**] |  | defaults to undefined|


### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **postChatFeedbackApiChatFeedbackInferenceIdPost_0**
> any postChatFeedbackApiChatFeedbackInferenceIdPost_0(feedbackRequest, )

Post feedback for Arthur Chat.

### Example

```typescript
import {
    ChatApi,
    Configuration,
    FeedbackRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ChatApi(configuration);

let feedbackRequest: FeedbackRequest; //
let inferenceId: string; // (default to undefined)

const { status, data } = await apiInstance.postChatFeedbackApiChatFeedbackInferenceIdPost_0(
    feedbackRequest,
    inferenceId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **feedbackRequest** | **FeedbackRequest**|  | |
| **inferenceId** | [**string**] |  | defaults to undefined|


### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **updateDefaultTaskApiChatDefaultTaskPut**
> ChatDefaultTaskResponse updateDefaultTaskApiChatDefaultTaskPut(chatDefaultTaskRequest)

Update the default task for Arthur Chat.

### Example

```typescript
import {
    ChatApi,
    Configuration,
    ChatDefaultTaskRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ChatApi(configuration);

let chatDefaultTaskRequest: ChatDefaultTaskRequest; //

const { status, data } = await apiInstance.updateDefaultTaskApiChatDefaultTaskPut(
    chatDefaultTaskRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **chatDefaultTaskRequest** | **ChatDefaultTaskRequest**|  | |


### Return type

**ChatDefaultTaskResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **uploadEmbeddingsFileApiChatFilesPost**
> FileUploadResult uploadEmbeddingsFileApiChatFilesPost()

Upload files via form-data. Only PDF, CSV, TXT types accepted.

### Example

```typescript
import {
    ChatApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ChatApi(configuration);

let file: File; // (default to undefined)
let isGlobal: boolean; // (optional) (default to false)

const { status, data } = await apiInstance.uploadEmbeddingsFileApiChatFilesPost(
    file,
    isGlobal
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **file** | [**File**] |  | defaults to undefined|
| **isGlobal** | [**boolean**] |  | (optional) defaults to false|


### Return type

**FileUploadResult**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

