# _generated.RAGExperimentsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**attach_notebook_to_rag_experiment_api_v1_rag_experiments_experiment_id_notebook_patch**](RAGExperimentsApi.md#attach_notebook_to_rag_experiment_api_v1_rag_experiments_experiment_id_notebook_patch) | **PATCH** /api/v1/rag_experiments/{experiment_id}/notebook | Attach notebook to RAG experiment
[**create_rag_experiment_api_v1_tasks_task_id_rag_experiments_post**](RAGExperimentsApi.md#create_rag_experiment_api_v1_tasks_task_id_rag_experiments_post) | **POST** /api/v1/tasks/{task_id}/rag_experiments | Create and run a RAG experiment
[**delete_rag_experiment_api_v1_rag_experiments_experiment_id_delete**](RAGExperimentsApi.md#delete_rag_experiment_api_v1_rag_experiments_experiment_id_delete) | **DELETE** /api/v1/rag_experiments/{experiment_id} | Delete RAG experiment
[**get_rag_config_results_api_v1_rag_experiments_experiment_id_rag_configs_rag_config_key_results_get**](RAGExperimentsApi.md#get_rag_config_results_api_v1_rag_experiments_experiment_id_rag_configs_rag_config_key_results_get) | **GET** /api/v1/rag_experiments/{experiment_id}/rag_configs/{rag_config_key}/results | Get RAG config results
[**get_rag_experiment_api_v1_rag_experiments_experiment_id_get**](RAGExperimentsApi.md#get_rag_experiment_api_v1_rag_experiments_experiment_id_get) | **GET** /api/v1/rag_experiments/{experiment_id} | Get RAG experiment details
[**get_rag_experiment_test_cases_api_v1_rag_experiments_experiment_id_test_cases_get**](RAGExperimentsApi.md#get_rag_experiment_test_cases_api_v1_rag_experiments_experiment_id_test_cases_get) | **GET** /api/v1/rag_experiments/{experiment_id}/test_cases | Get experiment test cases
[**list_rag_experiments_api_v1_tasks_task_id_rag_experiments_get**](RAGExperimentsApi.md#list_rag_experiments_api_v1_tasks_task_id_rag_experiments_get) | **GET** /api/v1/tasks/{task_id}/rag_experiments | List RAG experiments


# **attach_notebook_to_rag_experiment_api_v1_rag_experiments_experiment_id_notebook_patch**
> RagExperimentSummary attach_notebook_to_rag_experiment_api_v1_rag_experiments_experiment_id_notebook_patch(experiment_id, notebook_id)

Attach notebook to RAG experiment

Attach a RAG notebook to an existing experiment

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.rag_experiment_summary import RagExperimentSummary
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
    api_instance = _generated.RAGExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | ID of the experiment
    notebook_id = 'notebook_id_example' # str | ID of the notebook to attach

    try:
        # Attach notebook to RAG experiment
        api_response = api_instance.attach_notebook_to_rag_experiment_api_v1_rag_experiments_experiment_id_notebook_patch(experiment_id, notebook_id)
        print("The response of RAGExperimentsApi->attach_notebook_to_rag_experiment_api_v1_rag_experiments_experiment_id_notebook_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGExperimentsApi->attach_notebook_to_rag_experiment_api_v1_rag_experiments_experiment_id_notebook_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| ID of the experiment | 
 **notebook_id** | **str**| ID of the notebook to attach | 

### Return type

[**RagExperimentSummary**](RagExperimentSummary.md)

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

# **create_rag_experiment_api_v1_tasks_task_id_rag_experiments_post**
> RagExperimentSummary create_rag_experiment_api_v1_tasks_task_id_rag_experiments_post(task_id, create_rag_experiment_request)

Create and run a RAG experiment

Create a new RAG experiment and initiate execution

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.create_rag_experiment_request import CreateRagExperimentRequest
from _generated.models.rag_experiment_summary import RagExperimentSummary
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
    api_instance = _generated.RAGExperimentsApi(api_client)
    task_id = 'task_id_example' # str | 
    create_rag_experiment_request = _generated.CreateRagExperimentRequest() # CreateRagExperimentRequest | 

    try:
        # Create and run a RAG experiment
        api_response = api_instance.create_rag_experiment_api_v1_tasks_task_id_rag_experiments_post(task_id, create_rag_experiment_request)
        print("The response of RAGExperimentsApi->create_rag_experiment_api_v1_tasks_task_id_rag_experiments_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGExperimentsApi->create_rag_experiment_api_v1_tasks_task_id_rag_experiments_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **create_rag_experiment_request** | [**CreateRagExperimentRequest**](CreateRagExperimentRequest.md)|  | 

### Return type

[**RagExperimentSummary**](RagExperimentSummary.md)

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

# **delete_rag_experiment_api_v1_rag_experiments_experiment_id_delete**
> delete_rag_experiment_api_v1_rag_experiments_experiment_id_delete(experiment_id)

Delete RAG experiment

Delete a RAG experiment and all its associated data

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
    api_instance = _generated.RAGExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | The ID of the experiment to delete

    try:
        # Delete RAG experiment
        api_instance.delete_rag_experiment_api_v1_rag_experiments_experiment_id_delete(experiment_id)
    except Exception as e:
        print("Exception when calling RAGExperimentsApi->delete_rag_experiment_api_v1_rag_experiments_experiment_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| The ID of the experiment to delete | 

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
**204** | Experiment deleted successfully. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_rag_config_results_api_v1_rag_experiments_experiment_id_rag_configs_rag_config_key_results_get**
> RagConfigResultListResponse get_rag_config_results_api_v1_rag_experiments_experiment_id_rag_configs_rag_config_key_results_get(experiment_id, rag_config_key, sort=sort, page_size=page_size, page=page)

Get RAG config results

Get paginated list of results for a specific RAG configuration within an experiment (supports both saved and unsaved configs)

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.rag_config_result_list_response import RagConfigResultListResponse
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
    api_instance = _generated.RAGExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | The ID of the experiment
    rag_config_key = 'rag_config_key_example' # str | The RAG config key (format: 'saved:setting_config_id:version' or 'unsaved:uuid'). URL-encode colons as %3A
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get RAG config results
        api_response = api_instance.get_rag_config_results_api_v1_rag_experiments_experiment_id_rag_configs_rag_config_key_results_get(experiment_id, rag_config_key, sort=sort, page_size=page_size, page=page)
        print("The response of RAGExperimentsApi->get_rag_config_results_api_v1_rag_experiments_experiment_id_rag_configs_rag_config_key_results_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGExperimentsApi->get_rag_config_results_api_v1_rag_experiments_experiment_id_rag_configs_rag_config_key_results_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| The ID of the experiment | 
 **rag_config_key** | **str**| The RAG config key (format: &#39;saved:setting_config_id:version&#39; or &#39;unsaved:uuid&#39;). URL-encode colons as %3A | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**RagConfigResultListResponse**](RagConfigResultListResponse.md)

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

# **get_rag_experiment_api_v1_rag_experiments_experiment_id_get**
> RagExperimentDetail get_rag_experiment_api_v1_rag_experiments_experiment_id_get(experiment_id)

Get RAG experiment details

Get detailed information about a specific RAG experiment including summary results

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.rag_experiment_detail import RagExperimentDetail
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
    api_instance = _generated.RAGExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | The ID of the experiment to retrieve

    try:
        # Get RAG experiment details
        api_response = api_instance.get_rag_experiment_api_v1_rag_experiments_experiment_id_get(experiment_id)
        print("The response of RAGExperimentsApi->get_rag_experiment_api_v1_rag_experiments_experiment_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGExperimentsApi->get_rag_experiment_api_v1_rag_experiments_experiment_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| The ID of the experiment to retrieve | 

### Return type

[**RagExperimentDetail**](RagExperimentDetail.md)

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

# **get_rag_experiment_test_cases_api_v1_rag_experiments_experiment_id_test_cases_get**
> RagTestCaseListResponse get_rag_experiment_test_cases_api_v1_rag_experiments_experiment_id_test_cases_get(experiment_id, sort=sort, page_size=page_size, page=page)

Get experiment test cases

Get paginated list of test case results for a RAG experiment

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.rag_test_case_list_response import RagTestCaseListResponse
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
    api_instance = _generated.RAGExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | The ID of the experiment
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get experiment test cases
        api_response = api_instance.get_rag_experiment_test_cases_api_v1_rag_experiments_experiment_id_test_cases_get(experiment_id, sort=sort, page_size=page_size, page=page)
        print("The response of RAGExperimentsApi->get_rag_experiment_test_cases_api_v1_rag_experiments_experiment_id_test_cases_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGExperimentsApi->get_rag_experiment_test_cases_api_v1_rag_experiments_experiment_id_test_cases_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| The ID of the experiment | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**RagTestCaseListResponse**](RagTestCaseListResponse.md)

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

# **list_rag_experiments_api_v1_tasks_task_id_rag_experiments_get**
> RagExperimentListResponse list_rag_experiments_api_v1_tasks_task_id_rag_experiments_get(task_id, search=search, dataset_id=dataset_id, sort=sort, page_size=page_size, page=page)

List RAG experiments

List all RAG experiments for a task with optional filtering and pagination

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.rag_experiment_list_response import RagExperimentListResponse
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
    api_instance = _generated.RAGExperimentsApi(api_client)
    task_id = 'task_id_example' # str | 
    search = 'search_example' # str | Search text to filter experiments by name or description (optional)
    dataset_id = 'dataset_id_example' # str | Filter experiments by dataset ID (optional)
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # List RAG experiments
        api_response = api_instance.list_rag_experiments_api_v1_tasks_task_id_rag_experiments_get(task_id, search=search, dataset_id=dataset_id, sort=sort, page_size=page_size, page=page)
        print("The response of RAGExperimentsApi->list_rag_experiments_api_v1_tasks_task_id_rag_experiments_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGExperimentsApi->list_rag_experiments_api_v1_tasks_task_id_rag_experiments_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **search** | **str**| Search text to filter experiments by name or description | [optional] 
 **dataset_id** | **str**| Filter experiments by dataset ID | [optional] 
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

