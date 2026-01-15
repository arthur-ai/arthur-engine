# _generated.AgenticNotebooksApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_agentic_notebook_api_v1_tasks_task_id_agentic_notebooks_post**](AgenticNotebooksApi.md#create_agentic_notebook_api_v1_tasks_task_id_agentic_notebooks_post) | **POST** /api/v1/tasks/{task_id}/agentic_notebooks | Create an agentic notebook
[**delete_agentic_notebook_api_v1_agentic_notebooks_notebook_id_delete**](AgenticNotebooksApi.md#delete_agentic_notebook_api_v1_agentic_notebooks_notebook_id_delete) | **DELETE** /api/v1/agentic_notebooks/{notebook_id} | Delete agentic notebook
[**get_agentic_notebook_api_v1_agentic_notebooks_notebook_id_get**](AgenticNotebooksApi.md#get_agentic_notebook_api_v1_agentic_notebooks_notebook_id_get) | **GET** /api/v1/agentic_notebooks/{notebook_id} | Get agentic notebook details
[**get_agentic_notebook_history_api_v1_agentic_notebooks_notebook_id_history_get**](AgenticNotebooksApi.md#get_agentic_notebook_history_api_v1_agentic_notebooks_notebook_id_history_get) | **GET** /api/v1/agentic_notebooks/{notebook_id}/history | Get agentic notebook history
[**get_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_get**](AgenticNotebooksApi.md#get_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_get) | **GET** /api/v1/agentic_notebooks/{notebook_id}/state | Get agentic notebook state
[**list_agentic_notebooks_api_v1_tasks_task_id_agentic_notebooks_get**](AgenticNotebooksApi.md#list_agentic_notebooks_api_v1_tasks_task_id_agentic_notebooks_get) | **GET** /api/v1/tasks/{task_id}/agentic_notebooks | List agentic notebooks
[**set_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_put**](AgenticNotebooksApi.md#set_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_put) | **PUT** /api/v1/agentic_notebooks/{notebook_id}/state | Set agentic notebook state
[**update_agentic_notebook_api_v1_agentic_notebooks_notebook_id_put**](AgenticNotebooksApi.md#update_agentic_notebook_api_v1_agentic_notebooks_notebook_id_put) | **PUT** /api/v1/agentic_notebooks/{notebook_id} | Update agentic notebook metadata


# **create_agentic_notebook_api_v1_tasks_task_id_agentic_notebooks_post**
> AgenticNotebookDetail create_agentic_notebook_api_v1_tasks_task_id_agentic_notebooks_post(task_id, create_agentic_notebook_request)

Create an agentic notebook

Create a new agentic notebook for organizing experiments within a task

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_notebook_detail import AgenticNotebookDetail
from _generated.models.create_agentic_notebook_request import CreateAgenticNotebookRequest
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
    api_instance = _generated.AgenticNotebooksApi(api_client)
    task_id = 'task_id_example' # str | 
    create_agentic_notebook_request = _generated.CreateAgenticNotebookRequest() # CreateAgenticNotebookRequest | 

    try:
        # Create an agentic notebook
        api_response = api_instance.create_agentic_notebook_api_v1_tasks_task_id_agentic_notebooks_post(task_id, create_agentic_notebook_request)
        print("The response of AgenticNotebooksApi->create_agentic_notebook_api_v1_tasks_task_id_agentic_notebooks_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticNotebooksApi->create_agentic_notebook_api_v1_tasks_task_id_agentic_notebooks_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **create_agentic_notebook_request** | [**CreateAgenticNotebookRequest**](CreateAgenticNotebookRequest.md)|  | 

### Return type

[**AgenticNotebookDetail**](AgenticNotebookDetail.md)

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

# **delete_agentic_notebook_api_v1_agentic_notebooks_notebook_id_delete**
> delete_agentic_notebook_api_v1_agentic_notebooks_notebook_id_delete(notebook_id)

Delete agentic notebook

Delete an agentic notebook (experiments are kept)

### Example

* Bearer Authentication (API Key):

```python
import _generated
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
    api_instance = _generated.AgenticNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Agentic Notebook ID

    try:
        # Delete agentic notebook
        api_instance.delete_agentic_notebook_api_v1_agentic_notebooks_notebook_id_delete(notebook_id)
    except Exception as e:
        print("Exception when calling AgenticNotebooksApi->delete_agentic_notebook_api_v1_agentic_notebooks_notebook_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Agentic Notebook ID | 

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

# **get_agentic_notebook_api_v1_agentic_notebooks_notebook_id_get**
> AgenticNotebookDetail get_agentic_notebook_api_v1_agentic_notebooks_notebook_id_get(notebook_id)

Get agentic notebook details

Get detailed information about an agentic notebook including state and experiment history

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_notebook_detail import AgenticNotebookDetail
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
    api_instance = _generated.AgenticNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Agentic Notebook ID

    try:
        # Get agentic notebook details
        api_response = api_instance.get_agentic_notebook_api_v1_agentic_notebooks_notebook_id_get(notebook_id)
        print("The response of AgenticNotebooksApi->get_agentic_notebook_api_v1_agentic_notebooks_notebook_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticNotebooksApi->get_agentic_notebook_api_v1_agentic_notebooks_notebook_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Agentic Notebook ID | 

### Return type

[**AgenticNotebookDetail**](AgenticNotebookDetail.md)

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

# **get_agentic_notebook_history_api_v1_agentic_notebooks_notebook_id_history_get**
> AgenticExperimentListResponse get_agentic_notebook_history_api_v1_agentic_notebooks_notebook_id_history_get(notebook_id, sort=sort, page_size=page_size, page=page)

Get agentic notebook history

Get paginated list of experiments run from this agentic notebook

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_experiment_list_response import AgenticExperimentListResponse
from _generated.models.pagination_sort_method import PaginationSortMethod
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
    api_instance = _generated.AgenticNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Agentic Notebook ID
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get agentic notebook history
        api_response = api_instance.get_agentic_notebook_history_api_v1_agentic_notebooks_notebook_id_history_get(notebook_id, sort=sort, page_size=page_size, page=page)
        print("The response of AgenticNotebooksApi->get_agentic_notebook_history_api_v1_agentic_notebooks_notebook_id_history_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticNotebooksApi->get_agentic_notebook_history_api_v1_agentic_notebooks_notebook_id_history_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Agentic Notebook ID | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**AgenticExperimentListResponse**](AgenticExperimentListResponse.md)

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

# **get_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_get**
> AgenticNotebookStateResponse get_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_get(notebook_id)

Get agentic notebook state

Get the current state (draft configuration) of an agentic notebook

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_notebook_state_response import AgenticNotebookStateResponse
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
    api_instance = _generated.AgenticNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Agentic Notebook ID

    try:
        # Get agentic notebook state
        api_response = api_instance.get_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_get(notebook_id)
        print("The response of AgenticNotebooksApi->get_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticNotebooksApi->get_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Agentic Notebook ID | 

### Return type

[**AgenticNotebookStateResponse**](AgenticNotebookStateResponse.md)

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

# **list_agentic_notebooks_api_v1_tasks_task_id_agentic_notebooks_get**
> AgenticNotebookListResponse list_agentic_notebooks_api_v1_tasks_task_id_agentic_notebooks_get(task_id, name=name, sort=sort, page_size=page_size, page=page)

List agentic notebooks

List all agentic notebooks for a task with pagination and optional name search

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_notebook_list_response import AgenticNotebookListResponse
from _generated.models.pagination_sort_method import PaginationSortMethod
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
    api_instance = _generated.AgenticNotebooksApi(api_client)
    task_id = 'task_id_example' # str | 
    name = 'name_example' # str |  (optional)
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # List agentic notebooks
        api_response = api_instance.list_agentic_notebooks_api_v1_tasks_task_id_agentic_notebooks_get(task_id, name=name, sort=sort, page_size=page_size, page=page)
        print("The response of AgenticNotebooksApi->list_agentic_notebooks_api_v1_tasks_task_id_agentic_notebooks_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticNotebooksApi->list_agentic_notebooks_api_v1_tasks_task_id_agentic_notebooks_get: %s\n" % e)
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

[**AgenticNotebookListResponse**](AgenticNotebookListResponse.md)

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

# **set_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_put**
> AgenticNotebookDetail set_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_put(notebook_id, set_agentic_notebook_state_request)

Set agentic notebook state

Set the state (draft configuration) of an agentic notebook

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_notebook_detail import AgenticNotebookDetail
from _generated.models.set_agentic_notebook_state_request import SetAgenticNotebookStateRequest
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
    api_instance = _generated.AgenticNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Agentic Notebook ID
    set_agentic_notebook_state_request = _generated.SetAgenticNotebookStateRequest() # SetAgenticNotebookStateRequest | 

    try:
        # Set agentic notebook state
        api_response = api_instance.set_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_put(notebook_id, set_agentic_notebook_state_request)
        print("The response of AgenticNotebooksApi->set_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticNotebooksApi->set_agentic_notebook_state_api_v1_agentic_notebooks_notebook_id_state_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Agentic Notebook ID | 
 **set_agentic_notebook_state_request** | [**SetAgenticNotebookStateRequest**](SetAgenticNotebookStateRequest.md)|  | 

### Return type

[**AgenticNotebookDetail**](AgenticNotebookDetail.md)

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

# **update_agentic_notebook_api_v1_agentic_notebooks_notebook_id_put**
> AgenticNotebookDetail update_agentic_notebook_api_v1_agentic_notebooks_notebook_id_put(notebook_id, update_agentic_notebook_request)

Update agentic notebook metadata

Update agentic notebook name or description (not the state)

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_notebook_detail import AgenticNotebookDetail
from _generated.models.update_agentic_notebook_request import UpdateAgenticNotebookRequest
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
    api_instance = _generated.AgenticNotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Agentic Notebook ID
    update_agentic_notebook_request = _generated.UpdateAgenticNotebookRequest() # UpdateAgenticNotebookRequest | 

    try:
        # Update agentic notebook metadata
        api_response = api_instance.update_agentic_notebook_api_v1_agentic_notebooks_notebook_id_put(notebook_id, update_agentic_notebook_request)
        print("The response of AgenticNotebooksApi->update_agentic_notebook_api_v1_agentic_notebooks_notebook_id_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticNotebooksApi->update_agentic_notebook_api_v1_agentic_notebooks_notebook_id_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Agentic Notebook ID | 
 **update_agentic_notebook_request** | [**UpdateAgenticNotebookRequest**](UpdateAgenticNotebookRequest.md)|  | 

### Return type

[**AgenticNotebookDetail**](AgenticNotebookDetail.md)

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

