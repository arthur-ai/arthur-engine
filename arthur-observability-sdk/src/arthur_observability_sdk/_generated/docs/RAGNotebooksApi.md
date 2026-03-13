# arthur_observability_sdk._generated.RAGNotebooksApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_rag_notebook_api_v1_tasks_task_id_rag_notebooks_post**](RAGNotebooksApi.md#create_rag_notebook_api_v1_tasks_task_id_rag_notebooks_post) | **POST** /api/v1/tasks/{task_id}/rag_notebooks | Create a RAG notebook
[**delete_rag_notebook_api_v1_rag_notebooks_notebook_id_delete**](RAGNotebooksApi.md#delete_rag_notebook_api_v1_rag_notebooks_notebook_id_delete) | **DELETE** /api/v1/rag_notebooks/{notebook_id} | Delete RAG notebook
[**get_rag_notebook_api_v1_rag_notebooks_notebook_id_get**](RAGNotebooksApi.md#get_rag_notebook_api_v1_rag_notebooks_notebook_id_get) | **GET** /api/v1/rag_notebooks/{notebook_id} | Get RAG notebook details
[**get_rag_notebook_history_api_v1_rag_notebooks_notebook_id_history_get**](RAGNotebooksApi.md#get_rag_notebook_history_api_v1_rag_notebooks_notebook_id_history_get) | **GET** /api/v1/rag_notebooks/{notebook_id}/history | Get RAG notebook history
[**get_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_get**](RAGNotebooksApi.md#get_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_get) | **GET** /api/v1/rag_notebooks/{notebook_id}/state | Get RAG notebook state
[**list_rag_notebooks_api_v1_tasks_task_id_rag_notebooks_get**](RAGNotebooksApi.md#list_rag_notebooks_api_v1_tasks_task_id_rag_notebooks_get) | **GET** /api/v1/tasks/{task_id}/rag_notebooks | List RAG notebooks
[**set_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_put**](RAGNotebooksApi.md#set_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_put) | **PUT** /api/v1/rag_notebooks/{notebook_id}/state | Set RAG notebook state
[**update_rag_notebook_api_v1_rag_notebooks_notebook_id_put**](RAGNotebooksApi.md#update_rag_notebook_api_v1_rag_notebooks_notebook_id_put) | **PUT** /api/v1/rag_notebooks/{notebook_id} | Update RAG notebook metadata


# **create_rag_notebook_api_v1_tasks_task_id_rag_notebooks_post**
> RagNotebookDetail create_rag_notebook_api_v1_tasks_task_id_rag_notebooks_post(task_id, create_rag_notebook_request)

Create a RAG notebook

Create a new RAG notebook for organizing experiments within a task

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.create_rag_notebook_request import CreateRagNotebookRequest
from arthur_observability_sdk._generated.models.rag_notebook_detail import RagNotebookDetail
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: API Key
configuration = arthur_observability_sdk._generated.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.RAGNotebooksApi(api_client)
    task_id = 'task_id_example' # str | 
    create_rag_notebook_request = arthur_observability_sdk._generated.CreateRagNotebookRequest() # CreateRagNotebookRequest | 

    try:
        # Create a RAG notebook
        api_response = api_instance.create_rag_notebook_api_v1_tasks_task_id_rag_notebooks_post(task_id, create_rag_notebook_request)
        print("The response of RAGNotebooksApi->create_rag_notebook_api_v1_tasks_task_id_rag_notebooks_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGNotebooksApi->create_rag_notebook_api_v1_tasks_task_id_rag_notebooks_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **create_rag_notebook_request** | [**CreateRagNotebookRequest**](CreateRagNotebookRequest.md)|  | 

### Return type

[**RagNotebookDetail**](RagNotebookDetail.md)

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

# **delete_rag_notebook_api_v1_rag_notebooks_notebook_id_delete**
> delete_rag_notebook_api_v1_rag_notebooks_notebook_id_delete(notebook_id)

Delete RAG notebook

Delete a RAG notebook (experiments are kept)

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: API Key
configuration = arthur_observability_sdk._generated.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.RAGNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | RAG Notebook ID

    try:
        # Delete RAG notebook
        api_instance.delete_rag_notebook_api_v1_rag_notebooks_notebook_id_delete(notebook_id)
    except Exception as e:
        print("Exception when calling RAGNotebooksApi->delete_rag_notebook_api_v1_rag_notebooks_notebook_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| RAG Notebook ID | 

### Return type

void (empty response body)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_rag_notebook_api_v1_rag_notebooks_notebook_id_get**
> RagNotebookDetail get_rag_notebook_api_v1_rag_notebooks_notebook_id_get(notebook_id)

Get RAG notebook details

Get detailed information about a RAG notebook including state and experiment history

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.rag_notebook_detail import RagNotebookDetail
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: API Key
configuration = arthur_observability_sdk._generated.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.RAGNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | RAG Notebook ID

    try:
        # Get RAG notebook details
        api_response = api_instance.get_rag_notebook_api_v1_rag_notebooks_notebook_id_get(notebook_id)
        print("The response of RAGNotebooksApi->get_rag_notebook_api_v1_rag_notebooks_notebook_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGNotebooksApi->get_rag_notebook_api_v1_rag_notebooks_notebook_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| RAG Notebook ID | 

### Return type

[**RagNotebookDetail**](RagNotebookDetail.md)

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

# **get_rag_notebook_history_api_v1_rag_notebooks_notebook_id_history_get**
> RagExperimentListResponse get_rag_notebook_history_api_v1_rag_notebooks_notebook_id_history_get(notebook_id, sort=sort, page_size=page_size, page=page)

Get RAG notebook history

Get paginated list of experiments run from this RAG notebook

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.rag_experiment_list_response import RagExperimentListResponse
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: API Key
configuration = arthur_observability_sdk._generated.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.RAGNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | RAG Notebook ID
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get RAG notebook history
        api_response = api_instance.get_rag_notebook_history_api_v1_rag_notebooks_notebook_id_history_get(notebook_id, sort=sort, page_size=page_size, page=page)
        print("The response of RAGNotebooksApi->get_rag_notebook_history_api_v1_rag_notebooks_notebook_id_history_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGNotebooksApi->get_rag_notebook_history_api_v1_rag_notebooks_notebook_id_history_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| RAG Notebook ID | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**RagExperimentListResponse**](RagExperimentListResponse.md)

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

# **get_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_get**
> RagNotebookStateResponse get_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_get(notebook_id)

Get RAG notebook state

Get the current state (draft configuration) of a RAG notebook

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.rag_notebook_state_response import RagNotebookStateResponse
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: API Key
configuration = arthur_observability_sdk._generated.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.RAGNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | RAG Notebook ID

    try:
        # Get RAG notebook state
        api_response = api_instance.get_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_get(notebook_id)
        print("The response of RAGNotebooksApi->get_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGNotebooksApi->get_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| RAG Notebook ID | 

### Return type

[**RagNotebookStateResponse**](RagNotebookStateResponse.md)

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

# **list_rag_notebooks_api_v1_tasks_task_id_rag_notebooks_get**
> RagNotebookListResponse list_rag_notebooks_api_v1_tasks_task_id_rag_notebooks_get(task_id, name=name, sort=sort, page_size=page_size, page=page)

List RAG notebooks

List all RAG notebooks for a task with pagination and optional name search

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.rag_notebook_list_response import RagNotebookListResponse
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: API Key
configuration = arthur_observability_sdk._generated.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.RAGNotebooksApi(api_client)
    task_id = 'task_id_example' # str | 
    name = 'name_example' # str |  (optional)
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # List RAG notebooks
        api_response = api_instance.list_rag_notebooks_api_v1_tasks_task_id_rag_notebooks_get(task_id, name=name, sort=sort, page_size=page_size, page=page)
        print("The response of RAGNotebooksApi->list_rag_notebooks_api_v1_tasks_task_id_rag_notebooks_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGNotebooksApi->list_rag_notebooks_api_v1_tasks_task_id_rag_notebooks_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **name** | **str**|  | [optional] 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**RagNotebookListResponse**](RagNotebookListResponse.md)

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

# **set_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_put**
> RagNotebookDetail set_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_put(notebook_id, set_rag_notebook_state_request)

Set RAG notebook state

Set the state (draft configuration) of a RAG notebook

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.rag_notebook_detail import RagNotebookDetail
from arthur_observability_sdk._generated.models.set_rag_notebook_state_request import SetRagNotebookStateRequest
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: API Key
configuration = arthur_observability_sdk._generated.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.RAGNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | RAG Notebook ID
    set_rag_notebook_state_request = arthur_observability_sdk._generated.SetRagNotebookStateRequest() # SetRagNotebookStateRequest | 

    try:
        # Set RAG notebook state
        api_response = api_instance.set_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_put(notebook_id, set_rag_notebook_state_request)
        print("The response of RAGNotebooksApi->set_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGNotebooksApi->set_rag_notebook_state_api_v1_rag_notebooks_notebook_id_state_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| RAG Notebook ID | 
 **set_rag_notebook_state_request** | [**SetRagNotebookStateRequest**](SetRagNotebookStateRequest.md)|  | 

### Return type

[**RagNotebookDetail**](RagNotebookDetail.md)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_rag_notebook_api_v1_rag_notebooks_notebook_id_put**
> RagNotebookDetail update_rag_notebook_api_v1_rag_notebooks_notebook_id_put(notebook_id, update_rag_notebook_request)

Update RAG notebook metadata

Update RAG notebook name or description (not the state)

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.rag_notebook_detail import RagNotebookDetail
from arthur_observability_sdk._generated.models.update_rag_notebook_request import UpdateRagNotebookRequest
from arthur_observability_sdk._generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = arthur_observability_sdk._generated.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization: API Key
configuration = arthur_observability_sdk._generated.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with arthur_observability_sdk._generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = arthur_observability_sdk._generated.RAGNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | RAG Notebook ID
    update_rag_notebook_request = arthur_observability_sdk._generated.UpdateRagNotebookRequest() # UpdateRagNotebookRequest | 

    try:
        # Update RAG notebook metadata
        api_response = api_instance.update_rag_notebook_api_v1_rag_notebooks_notebook_id_put(notebook_id, update_rag_notebook_request)
        print("The response of RAGNotebooksApi->update_rag_notebook_api_v1_rag_notebooks_notebook_id_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGNotebooksApi->update_rag_notebook_api_v1_rag_notebooks_notebook_id_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| RAG Notebook ID | 
 **update_rag_notebook_request** | [**UpdateRagNotebookRequest**](UpdateRagNotebookRequest.md)|  | 

### Return type

[**RagNotebookDetail**](RagNotebookDetail.md)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

