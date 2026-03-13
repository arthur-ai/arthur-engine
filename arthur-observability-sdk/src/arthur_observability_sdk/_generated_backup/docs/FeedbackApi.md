# _generated.FeedbackApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**post_feedback_api_v2_feedback_inference_id_post**](FeedbackApi.md#post_feedback_api_v2_feedback_inference_id_post) | **POST** /api/v2/feedback/{inference_id} | Post Feedback
[**query_feedback_api_v2_feedback_query_get**](FeedbackApi.md#query_feedback_api_v2_feedback_query_get) | **GET** /api/v2/feedback/query | Query Feedback


# **post_feedback_api_v2_feedback_inference_id_post**
> InferenceFeedbackResponse post_feedback_api_v2_feedback_inference_id_post(inference_id, feedback_request)

Post Feedback

Post feedback for LLM Application.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.feedback_request import FeedbackRequest
from _generated.models.inference_feedback_response import InferenceFeedbackResponse
from _generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = _generated.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: API Key
configuration = _generated.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with _generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = _generated.FeedbackApi(api_client)
    inference_id = 'inference_id_example' # str | 
    feedback_request = _generated.FeedbackRequest() # FeedbackRequest | 

    try:
        # Post Feedback
        api_response = api_instance.post_feedback_api_v2_feedback_inference_id_post(inference_id, feedback_request)
        print("The response of FeedbackApi->post_feedback_api_v2_feedback_inference_id_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling FeedbackApi->post_feedback_api_v2_feedback_inference_id_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **inference_id** | **str**|  | 
 **feedback_request** | [**FeedbackRequest**](FeedbackRequest.md)|  | 

### Return type

[**InferenceFeedbackResponse**](InferenceFeedbackResponse.md)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **query_feedback_api_v2_feedback_query_get**
> QueryFeedbackResponse query_feedback_api_v2_feedback_query_get(start_time=start_time, end_time=end_time, feedback_id=feedback_id, inference_id=inference_id, target=target, score=score, feedback_user_id=feedback_user_id, conversation_id=conversation_id, task_id=task_id, inference_user_id=inference_user_id, sort=sort, page_size=page_size, page=page)

Query Feedback

Paginated feedback querying. See parameters for available filters. Includes feedback from archived tasks and rules.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.query_feedback_response import QueryFeedbackResponse
from _generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = _generated.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: API Key
configuration = _generated.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with _generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = _generated.FeedbackApi(api_client)
    start_time = '2013-10-20T19:20:30+01:00' # datetime | Inclusive start date in ISO8601 string format (optional)
    end_time = '2013-10-20T19:20:30+01:00' # datetime | Exclusive end date in ISO8601 string format (optional)
    feedback_id = _generated.FeedbackId() # FeedbackId | Feedback ID to filter on (optional)
    inference_id = _generated.InferenceId() # InferenceId | Inference ID to filter on (optional)
    target = _generated.Target() # Target | Target of the feedback. Must be one of ['context', 'response_results', 'prompt_results'] (optional)
    score = _generated.Score() # Score | Score of the feedback. Must be an integer. (optional)
    feedback_user_id = 'feedback_user_id_example' # str | User ID of the user giving feedback to filter on (query will perform fuzzy search) (optional)
    conversation_id = _generated.ConversationId() # ConversationId | Conversation ID to filter on (optional)
    task_id = _generated.TaskId() # TaskId | Task ID to filter on (optional)
    inference_user_id = 'inference_user_id_example' # str | User ID of the user who created the inferences to filter on (query will perform fuzzy search) (optional)
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Query Feedback
        api_response = api_instance.query_feedback_api_v2_feedback_query_get(start_time=start_time, end_time=end_time, feedback_id=feedback_id, inference_id=inference_id, target=target, score=score, feedback_user_id=feedback_user_id, conversation_id=conversation_id, task_id=task_id, inference_user_id=inference_user_id, sort=sort, page_size=page_size, page=page)
        print("The response of FeedbackApi->query_feedback_api_v2_feedback_query_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling FeedbackApi->query_feedback_api_v2_feedback_query_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **start_time** | **datetime**| Inclusive start date in ISO8601 string format | [optional] 
 **end_time** | **datetime**| Exclusive end date in ISO8601 string format | [optional] 
 **feedback_id** | [**FeedbackId**](.md)| Feedback ID to filter on | [optional] 
 **inference_id** | [**InferenceId**](.md)| Inference ID to filter on | [optional] 
 **target** | [**Target**](.md)| Target of the feedback. Must be one of [&#39;context&#39;, &#39;response_results&#39;, &#39;prompt_results&#39;] | [optional] 
 **score** | [**Score**](.md)| Score of the feedback. Must be an integer. | [optional] 
 **feedback_user_id** | **str**| User ID of the user giving feedback to filter on (query will perform fuzzy search) | [optional] 
 **conversation_id** | [**ConversationId**](.md)| Conversation ID to filter on | [optional] 
 **task_id** | [**TaskId**](.md)| Task ID to filter on | [optional] 
 **inference_user_id** | **str**| User ID of the user who created the inferences to filter on (query will perform fuzzy search) | [optional] 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**QueryFeedbackResponse**](QueryFeedbackResponse.md)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

