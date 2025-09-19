# FeedbackApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**postFeedbackApiV2FeedbackInferenceIdPost**](#postfeedbackapiv2feedbackinferenceidpost) | **POST** /api/v2/feedback/{inference_id} | Post Feedback|
|[**queryFeedbackApiV2FeedbackQueryGet**](#queryfeedbackapiv2feedbackqueryget) | **GET** /api/v2/feedback/query | Query Feedback|

# **postFeedbackApiV2FeedbackInferenceIdPost**
> InferenceFeedbackResponse postFeedbackApiV2FeedbackInferenceIdPost(feedbackRequest, )

Post feedback for LLM Application.

### Example

```typescript
import {
    FeedbackApi,
    Configuration,
    FeedbackRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new FeedbackApi(configuration);

let feedbackRequest: FeedbackRequest; //
let inferenceId: string; // (default to undefined)

const { status, data } = await apiInstance.postFeedbackApiV2FeedbackInferenceIdPost(
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

**InferenceFeedbackResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **queryFeedbackApiV2FeedbackQueryGet**
> QueryFeedbackResponse queryFeedbackApiV2FeedbackQueryGet()

Paginated feedback querying. See parameters for available filters. Includes feedback from archived tasks and rules.

### Example

```typescript
import {
    FeedbackApi,
    Configuration,
    FeedbackId,
    InferenceId,
    Target,
    Score,
    ConversationId,
    TaskId
} from './api';

const configuration = new Configuration();
const apiInstance = new FeedbackApi(configuration);

let startTime: string; //Inclusive start date in ISO8601 string format (optional) (default to undefined)
let endTime: string; //Exclusive end date in ISO8601 string format (optional) (default to undefined)
let feedbackId: FeedbackId; //Feedback ID to filter on (optional) (default to undefined)
let inferenceId: InferenceId; //Inference ID to filter on (optional) (default to undefined)
let target: Target; //Target of the feedback. Must be one of [\'context\', \'response_results\', \'prompt_results\'] (optional) (default to undefined)
let score: Score; //Score of the feedback. Must be an integer. (optional) (default to undefined)
let feedbackUserId: string; //User ID of the user giving feedback to filter on (query will perform fuzzy search) (optional) (default to undefined)
let conversationId: ConversationId; //Conversation ID to filter on (optional) (default to undefined)
let taskId: TaskId; //Task ID to filter on (optional) (default to undefined)
let inferenceUserId: string; //User ID of the user who created the inferences to filter on (query will perform fuzzy search) (optional) (default to undefined)
let sort: PaginationSortMethod; //Sort the results (asc/desc) (optional) (default to undefined)
let pageSize: number; //Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
let page: number; //Page number (optional) (default to 0)

const { status, data } = await apiInstance.queryFeedbackApiV2FeedbackQueryGet(
    startTime,
    endTime,
    feedbackId,
    inferenceId,
    target,
    score,
    feedbackUserId,
    conversationId,
    taskId,
    inferenceUserId,
    sort,
    pageSize,
    page
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **startTime** | [**string**] | Inclusive start date in ISO8601 string format | (optional) defaults to undefined|
| **endTime** | [**string**] | Exclusive end date in ISO8601 string format | (optional) defaults to undefined|
| **feedbackId** | **FeedbackId** | Feedback ID to filter on | (optional) defaults to undefined|
| **inferenceId** | **InferenceId** | Inference ID to filter on | (optional) defaults to undefined|
| **target** | **Target** | Target of the feedback. Must be one of [\&#39;context\&#39;, \&#39;response_results\&#39;, \&#39;prompt_results\&#39;] | (optional) defaults to undefined|
| **score** | **Score** | Score of the feedback. Must be an integer. | (optional) defaults to undefined|
| **feedbackUserId** | [**string**] | User ID of the user giving feedback to filter on (query will perform fuzzy search) | (optional) defaults to undefined|
| **conversationId** | **ConversationId** | Conversation ID to filter on | (optional) defaults to undefined|
| **taskId** | **TaskId** | Task ID to filter on | (optional) defaults to undefined|
| **inferenceUserId** | [**string**] | User ID of the user who created the inferences to filter on (query will perform fuzzy search) | (optional) defaults to undefined|
| **sort** | **PaginationSortMethod** | Sort the results (asc/desc) | (optional) defaults to undefined|
| **pageSize** | [**number**] | Page size. Default is 10. Must be greater than 0 and less than 5000. | (optional) defaults to 10|
| **page** | [**number**] | Page number | (optional) defaults to 0|


### Return type

**QueryFeedbackResponse**

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

