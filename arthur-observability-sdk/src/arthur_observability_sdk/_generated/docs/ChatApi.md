# arthur_observability_sdk._generated.ChatApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**chat_request**](ChatApi.md#chat_request) | **POST** /api/chat/ | Chat
[**delete_file_api_chat_files_file_id_delete**](ChatApi.md#delete_file_api_chat_files_file_id_delete) | **DELETE** /api/chat/files/{file_id} | Delete File
[**get_conversations_api_chat_conversations_get**](ChatApi.md#get_conversations_api_chat_conversations_get) | **GET** /api/chat/conversations | Get Conversations
[**get_default_task_api_chat_default_task_get**](ChatApi.md#get_default_task_api_chat_default_task_get) | **GET** /api/chat/default_task | Get Default Task
[**get_files_api_chat_files_get**](ChatApi.md#get_files_api_chat_files_get) | **GET** /api/chat/files | Get Files
[**get_inference_document_context_api_chat_context_inference_id_get**](ChatApi.md#get_inference_document_context_api_chat_context_inference_id_get) | **GET** /api/chat/context/{inference_id} | Get Inference Document Context
[**post_chat_feedback_api_chat_feedback_inference_id_post**](ChatApi.md#post_chat_feedback_api_chat_feedback_inference_id_post) | **POST** /api/chat/feedback/{inference_id} | Post Chat Feedback
[**post_chat_feedback_api_chat_feedback_inference_id_post_0**](ChatApi.md#post_chat_feedback_api_chat_feedback_inference_id_post_0) | **POST** /api/chat/feedback/{inference_id} | Post Chat Feedback
[**update_default_task_api_chat_default_task_put**](ChatApi.md#update_default_task_api_chat_default_task_put) | **PUT** /api/chat/default_task | Update Default Task
[**upload_embeddings_file_api_chat_files_post**](ChatApi.md#upload_embeddings_file_api_chat_files_post) | **POST** /api/chat/files | Upload Embeddings File


# **chat_request**
> ChatResponse chat_request(chat_request)

Chat

Chat request for Arthur Chat

### Example


```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.chat_request import ChatRequest
from arthur_observability_sdk._generated.models.chat_response import ChatResponse
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.ChatApi(api_client)
    chat_request = arthur_observability_sdk._generated.ChatRequest() # ChatRequest | 

    try:
        # Chat
        api_response = api_instance.chat_request(chat_request)
        print("The response of ChatApi->chat_request:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ChatApi->chat_request: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **chat_request** | [**ChatRequest**](ChatRequest.md)|  | 

### Return type

[**ChatResponse**](ChatResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_file_api_chat_files_file_id_delete**
> object delete_file_api_chat_files_file_id_delete(file_id)

Delete File

Remove a file by ID. This action cannot be undone.

### Example


```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.ChatApi(api_client)
    file_id = 'file_id_example' # str | 

    try:
        # Delete File
        api_response = api_instance.delete_file_api_chat_files_file_id_delete(file_id)
        print("The response of ChatApi->delete_file_api_chat_files_file_id_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ChatApi->delete_file_api_chat_files_file_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **file_id** | **str**|  | 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_conversations_api_chat_conversations_get**
> PageConversationBaseResponse get_conversations_api_chat_conversations_get(page=page, size=size)

Get Conversations

Get list of conversation IDs.

### Example


```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.page_conversation_base_response import PageConversationBaseResponse
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.ChatApi(api_client)
    page = 1 # int |  (optional) (default to 1)
    size = 50 # int |  (optional) (default to 50)

    try:
        # Get Conversations
        api_response = api_instance.get_conversations_api_chat_conversations_get(page=page, size=size)
        print("The response of ChatApi->get_conversations_api_chat_conversations_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ChatApi->get_conversations_api_chat_conversations_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **page** | **int**|  | [optional] [default to 1]
 **size** | **int**|  | [optional] [default to 50]

### Return type

[**PageConversationBaseResponse**](PageConversationBaseResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_default_task_api_chat_default_task_get**
> ChatDefaultTaskResponse get_default_task_api_chat_default_task_get()

Get Default Task

Get the default task for Arthur Chat.

### Example


```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.chat_default_task_response import ChatDefaultTaskResponse
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.ChatApi(api_client)

    try:
        # Get Default Task
        api_response = api_instance.get_default_task_api_chat_default_task_get()
        print("The response of ChatApi->get_default_task_api_chat_default_task_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ChatApi->get_default_task_api_chat_default_task_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**ChatDefaultTaskResponse**](ChatDefaultTaskResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_files_api_chat_files_get**
> List[ExternalDocument] get_files_api_chat_files_get()

Get Files

List uploaded files. Only files that are global or owned by the caller are returned.

### Example


```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.external_document import ExternalDocument
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.ChatApi(api_client)

    try:
        # Get Files
        api_response = api_instance.get_files_api_chat_files_get()
        print("The response of ChatApi->get_files_api_chat_files_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ChatApi->get_files_api_chat_files_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**List[ExternalDocument]**](ExternalDocument.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_inference_document_context_api_chat_context_inference_id_get**
> List[ChatDocumentContext] get_inference_document_context_api_chat_context_inference_id_get(inference_id)

Get Inference Document Context

Get document context used for a past inference ID.

### Example


```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.chat_document_context import ChatDocumentContext
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.ChatApi(api_client)
    inference_id = 'inference_id_example' # str | 

    try:
        # Get Inference Document Context
        api_response = api_instance.get_inference_document_context_api_chat_context_inference_id_get(inference_id)
        print("The response of ChatApi->get_inference_document_context_api_chat_context_inference_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ChatApi->get_inference_document_context_api_chat_context_inference_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **inference_id** | **str**|  | 

### Return type

[**List[ChatDocumentContext]**](ChatDocumentContext.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **post_chat_feedback_api_chat_feedback_inference_id_post**
> object post_chat_feedback_api_chat_feedback_inference_id_post(inference_id, feedback_request)

Post Chat Feedback

Post feedback for Arthur Chat.

### Example


```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.feedback_request import FeedbackRequest
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.ChatApi(api_client)
    inference_id = 'inference_id_example' # str | 
    feedback_request = arthur_observability_sdk._generated.FeedbackRequest() # FeedbackRequest | 

    try:
        # Post Chat Feedback
        api_response = api_instance.post_chat_feedback_api_chat_feedback_inference_id_post(inference_id, feedback_request)
        print("The response of ChatApi->post_chat_feedback_api_chat_feedback_inference_id_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ChatApi->post_chat_feedback_api_chat_feedback_inference_id_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **inference_id** | **str**|  | 
 **feedback_request** | [**FeedbackRequest**](FeedbackRequest.md)|  | 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **post_chat_feedback_api_chat_feedback_inference_id_post_0**
> object post_chat_feedback_api_chat_feedback_inference_id_post_0(inference_id, feedback_request)

Post Chat Feedback

Post feedback for Arthur Chat.

### Example


```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.feedback_request import FeedbackRequest
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.ChatApi(api_client)
    inference_id = 'inference_id_example' # str | 
    feedback_request = arthur_observability_sdk._generated.FeedbackRequest() # FeedbackRequest | 

    try:
        # Post Chat Feedback
        api_response = api_instance.post_chat_feedback_api_chat_feedback_inference_id_post_0(inference_id, feedback_request)
        print("The response of ChatApi->post_chat_feedback_api_chat_feedback_inference_id_post_0:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ChatApi->post_chat_feedback_api_chat_feedback_inference_id_post_0: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **inference_id** | **str**|  | 
 **feedback_request** | [**FeedbackRequest**](FeedbackRequest.md)|  | 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_default_task_api_chat_default_task_put**
> ChatDefaultTaskResponse update_default_task_api_chat_default_task_put(chat_default_task_request)

Update Default Task

Update the default task for Arthur Chat.

### Example


```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.chat_default_task_request import ChatDefaultTaskRequest
from arthur_observability_sdk._generated.models.chat_default_task_response import ChatDefaultTaskResponse
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.ChatApi(api_client)
    chat_default_task_request = arthur_observability_sdk._generated.ChatDefaultTaskRequest() # ChatDefaultTaskRequest | 

    try:
        # Update Default Task
        api_response = api_instance.update_default_task_api_chat_default_task_put(chat_default_task_request)
        print("The response of ChatApi->update_default_task_api_chat_default_task_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ChatApi->update_default_task_api_chat_default_task_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **chat_default_task_request** | [**ChatDefaultTaskRequest**](ChatDefaultTaskRequest.md)|  | 

### Return type

[**ChatDefaultTaskResponse**](ChatDefaultTaskResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **upload_embeddings_file_api_chat_files_post**
> FileUploadResult upload_embeddings_file_api_chat_files_post(file, is_global=is_global)

Upload Embeddings File

Upload files via form-data. Only PDF, CSV, TXT types accepted.

### Example


```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.file_upload_result import FileUploadResult
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.ChatApi(api_client)
    file = None # bytearray | 
    is_global = False # bool |  (optional) (default to False)

    try:
        # Upload Embeddings File
        api_response = api_instance.upload_embeddings_file_api_chat_files_post(file, is_global=is_global)
        print("The response of ChatApi->upload_embeddings_file_api_chat_files_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ChatApi->upload_embeddings_file_api_chat_files_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **file** | **bytearray**|  | 
 **is_global** | **bool**|  | [optional] [default to False]

### Return type

[**FileUploadResult**](FileUploadResult.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

