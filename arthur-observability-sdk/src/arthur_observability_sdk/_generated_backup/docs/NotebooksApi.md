# _generated.NotebooksApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_notebook_api_v1_tasks_task_id_notebooks_post**](NotebooksApi.md#create_notebook_api_v1_tasks_task_id_notebooks_post) | **POST** /api/v1/tasks/{task_id}/notebooks | Create a notebook
[**delete_notebook_api_v1_notebooks_notebook_id_delete**](NotebooksApi.md#delete_notebook_api_v1_notebooks_notebook_id_delete) | **DELETE** /api/v1/notebooks/{notebook_id} | Delete notebook
[**get_notebook_api_v1_notebooks_notebook_id_get**](NotebooksApi.md#get_notebook_api_v1_notebooks_notebook_id_get) | **GET** /api/v1/notebooks/{notebook_id} | Get notebook details
[**get_notebook_history_api_v1_notebooks_notebook_id_history_get**](NotebooksApi.md#get_notebook_history_api_v1_notebooks_notebook_id_history_get) | **GET** /api/v1/notebooks/{notebook_id}/history | Get notebook history
[**get_notebook_state_api_v1_notebooks_notebook_id_state_get**](NotebooksApi.md#get_notebook_state_api_v1_notebooks_notebook_id_state_get) | **GET** /api/v1/notebooks/{notebook_id}/state | Get notebook state
[**list_notebooks_api_v1_tasks_task_id_notebooks_get**](NotebooksApi.md#list_notebooks_api_v1_tasks_task_id_notebooks_get) | **GET** /api/v1/tasks/{task_id}/notebooks | List notebooks
[**set_notebook_state_api_v1_notebooks_notebook_id_state_put**](NotebooksApi.md#set_notebook_state_api_v1_notebooks_notebook_id_state_put) | **PUT** /api/v1/notebooks/{notebook_id}/state | Set notebook state
[**update_notebook_api_v1_notebooks_notebook_id_put**](NotebooksApi.md#update_notebook_api_v1_notebooks_notebook_id_put) | **PUT** /api/v1/notebooks/{notebook_id} | Update notebook metadata


# **create_notebook_api_v1_tasks_task_id_notebooks_post**
> NotebookDetail create_notebook_api_v1_tasks_task_id_notebooks_post(task_id, create_notebook_request)

Create a notebook

Create a new notebook for organizing experiments within a task

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.create_notebook_request import CreateNotebookRequest
from _generated.models.notebook_detail import NotebookDetail
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
    api_instance = _generated.NotebooksApi(api_client)
    task_id = 'task_id_example' # str | 
    create_notebook_request = _generated.CreateNotebookRequest() # CreateNotebookRequest | 

    try:
        # Create a notebook
        api_response = api_instance.create_notebook_api_v1_tasks_task_id_notebooks_post(task_id, create_notebook_request)
        print("The response of NotebooksApi->create_notebook_api_v1_tasks_task_id_notebooks_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling NotebooksApi->create_notebook_api_v1_tasks_task_id_notebooks_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **create_notebook_request** | [**CreateNotebookRequest**](CreateNotebookRequest.md)|  | 

### Return type

[**NotebookDetail**](NotebookDetail.md)

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

# **delete_notebook_api_v1_notebooks_notebook_id_delete**
> delete_notebook_api_v1_notebooks_notebook_id_delete(notebook_id)

Delete notebook

Delete a notebook (experiments are kept)

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
    api_instance = _generated.NotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Notebook ID

    try:
        # Delete notebook
        api_instance.delete_notebook_api_v1_notebooks_notebook_id_delete(notebook_id)
    except Exception as e:
        print("Exception when calling NotebooksApi->delete_notebook_api_v1_notebooks_notebook_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Notebook ID | 

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

# **get_notebook_api_v1_notebooks_notebook_id_get**
> NotebookDetail get_notebook_api_v1_notebooks_notebook_id_get(notebook_id)

Get notebook details

Get detailed information about a notebook including state and experiment history

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.notebook_detail import NotebookDetail
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
    api_instance = _generated.NotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Notebook ID

    try:
        # Get notebook details
        api_response = api_instance.get_notebook_api_v1_notebooks_notebook_id_get(notebook_id)
        print("The response of NotebooksApi->get_notebook_api_v1_notebooks_notebook_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling NotebooksApi->get_notebook_api_v1_notebooks_notebook_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Notebook ID | 

### Return type

[**NotebookDetail**](NotebookDetail.md)

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

# **get_notebook_history_api_v1_notebooks_notebook_id_history_get**
> PromptExperimentListResponse get_notebook_history_api_v1_notebooks_notebook_id_history_get(notebook_id, sort=sort, page_size=page_size, page=page)

Get notebook history

Get paginated list of experiments run from this notebook

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.prompt_experiment_list_response import PromptExperimentListResponse
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
    api_instance = _generated.NotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Notebook ID
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get notebook history
        api_response = api_instance.get_notebook_history_api_v1_notebooks_notebook_id_history_get(notebook_id, sort=sort, page_size=page_size, page=page)
        print("The response of NotebooksApi->get_notebook_history_api_v1_notebooks_notebook_id_history_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling NotebooksApi->get_notebook_history_api_v1_notebooks_notebook_id_history_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Notebook ID | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**PromptExperimentListResponse**](PromptExperimentListResponse.md)

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

# **get_notebook_state_api_v1_notebooks_notebook_id_state_get**
> NotebookStateOutput get_notebook_state_api_v1_notebooks_notebook_id_state_get(notebook_id)

Get notebook state

Get the current state (draft configuration) of a notebook

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.notebook_state_output import NotebookStateOutput
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
    api_instance = _generated.NotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Notebook ID

    try:
        # Get notebook state
        api_response = api_instance.get_notebook_state_api_v1_notebooks_notebook_id_state_get(notebook_id)
        print("The response of NotebooksApi->get_notebook_state_api_v1_notebooks_notebook_id_state_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling NotebooksApi->get_notebook_state_api_v1_notebooks_notebook_id_state_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Notebook ID | 

### Return type

[**NotebookStateOutput**](NotebookStateOutput.md)

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

# **list_notebooks_api_v1_tasks_task_id_notebooks_get**
> NotebookListResponse list_notebooks_api_v1_tasks_task_id_notebooks_get(task_id, name=name, sort=sort, page_size=page_size, page=page)

List notebooks

List all notebooks for a task with pagination and optional name search

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.notebook_list_response import NotebookListResponse
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
    api_instance = _generated.NotebooksApi(api_client)
    task_id = 'task_id_example' # str | 
    name = 'name_example' # str |  (optional)
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # List notebooks
        api_response = api_instance.list_notebooks_api_v1_tasks_task_id_notebooks_get(task_id, name=name, sort=sort, page_size=page_size, page=page)
        print("The response of NotebooksApi->list_notebooks_api_v1_tasks_task_id_notebooks_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling NotebooksApi->list_notebooks_api_v1_tasks_task_id_notebooks_get: %s\n" % e)
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

[**NotebookListResponse**](NotebookListResponse.md)

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

# **set_notebook_state_api_v1_notebooks_notebook_id_state_put**
> NotebookDetail set_notebook_state_api_v1_notebooks_notebook_id_state_put(notebook_id, set_notebook_state_request)

Set notebook state

Set the state (draft configuration) of a notebook

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.notebook_detail import NotebookDetail
from _generated.models.set_notebook_state_request import SetNotebookStateRequest
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
    api_instance = _generated.NotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Notebook ID
    set_notebook_state_request = _generated.SetNotebookStateRequest() # SetNotebookStateRequest | 

    try:
        # Set notebook state
        api_response = api_instance.set_notebook_state_api_v1_notebooks_notebook_id_state_put(notebook_id, set_notebook_state_request)
        print("The response of NotebooksApi->set_notebook_state_api_v1_notebooks_notebook_id_state_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling NotebooksApi->set_notebook_state_api_v1_notebooks_notebook_id_state_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Notebook ID | 
 **set_notebook_state_request** | [**SetNotebookStateRequest**](SetNotebookStateRequest.md)|  | 

### Return type

[**NotebookDetail**](NotebookDetail.md)

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

# **update_notebook_api_v1_notebooks_notebook_id_put**
> NotebookDetail update_notebook_api_v1_notebooks_notebook_id_put(notebook_id, update_notebook_request)

Update notebook metadata

Update notebook name or description (not the state)

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.notebook_detail import NotebookDetail
from _generated.models.update_notebook_request import UpdateNotebookRequest
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
    api_instance = _generated.NotebooksApi(api_client)
    notebook_id = 'notebook_id_example' # str | Notebook ID
    update_notebook_request = _generated.UpdateNotebookRequest() # UpdateNotebookRequest | 

    try:
        # Update notebook metadata
        api_response = api_instance.update_notebook_api_v1_notebooks_notebook_id_put(notebook_id, update_notebook_request)
        print("The response of NotebooksApi->update_notebook_api_v1_notebooks_notebook_id_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling NotebooksApi->update_notebook_api_v1_notebooks_notebook_id_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **notebook_id** | **str**| Notebook ID | 
 **update_notebook_request** | [**UpdateNotebookRequest**](UpdateNotebookRequest.md)|  | 

### Return type

[**NotebookDetail**](NotebookDetail.md)

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

