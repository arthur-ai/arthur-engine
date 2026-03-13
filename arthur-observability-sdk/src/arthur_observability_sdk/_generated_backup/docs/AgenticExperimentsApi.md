# _generated.AgenticExperimentsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**attach_notebook_to_agentic_experiment_api_v1_agentic_experiments_experiment_id_notebook_patch**](AgenticExperimentsApi.md#attach_notebook_to_agentic_experiment_api_v1_agentic_experiments_experiment_id_notebook_patch) | **PATCH** /api/v1/agentic_experiments/{experiment_id}/notebook | Attach notebook to agentic experiment
[**create_agentic_experiment_api_v1_tasks_task_id_agentic_experiments_post**](AgenticExperimentsApi.md#create_agentic_experiment_api_v1_tasks_task_id_agentic_experiments_post) | **POST** /api/v1/tasks/{task_id}/agentic_experiments | Create and run an agentic experiment
[**delete_agentic_experiment_api_v1_agentic_experiments_experiment_id_delete**](AgenticExperimentsApi.md#delete_agentic_experiment_api_v1_agentic_experiments_experiment_id_delete) | **DELETE** /api/v1/agentic_experiments/{experiment_id} | Delete agentic experiment
[**get_agentic_experiment_api_v1_agentic_experiments_experiment_id_get**](AgenticExperimentsApi.md#get_agentic_experiment_api_v1_agentic_experiments_experiment_id_get) | **GET** /api/v1/agentic_experiments/{experiment_id} | Get agentic experiment details
[**get_agentic_experiment_test_cases_api_v1_agentic_experiments_experiment_id_test_cases_get**](AgenticExperimentsApi.md#get_agentic_experiment_test_cases_api_v1_agentic_experiments_experiment_id_test_cases_get) | **GET** /api/v1/agentic_experiments/{experiment_id}/test_cases | Get experiment test cases
[**list_agentic_experiments_api_v1_tasks_task_id_agentic_experiments_get**](AgenticExperimentsApi.md#list_agentic_experiments_api_v1_tasks_task_id_agentic_experiments_get) | **GET** /api/v1/tasks/{task_id}/agentic_experiments | List agentic experiments


# **attach_notebook_to_agentic_experiment_api_v1_agentic_experiments_experiment_id_notebook_patch**
> AgenticExperimentSummary attach_notebook_to_agentic_experiment_api_v1_agentic_experiments_experiment_id_notebook_patch(experiment_id, notebook_id)

Attach notebook to agentic experiment

Attach an agentic notebook to an existing experiment

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_experiment_summary import AgenticExperimentSummary
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
    api_instance = _generated.AgenticExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | ID of the experiment
    notebook_id = 'notebook_id_example' # str | ID of the notebook to attach

    try:
        # Attach notebook to agentic experiment
        api_response = api_instance.attach_notebook_to_agentic_experiment_api_v1_agentic_experiments_experiment_id_notebook_patch(experiment_id, notebook_id)
        print("The response of AgenticExperimentsApi->attach_notebook_to_agentic_experiment_api_v1_agentic_experiments_experiment_id_notebook_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticExperimentsApi->attach_notebook_to_agentic_experiment_api_v1_agentic_experiments_experiment_id_notebook_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| ID of the experiment | 
 **notebook_id** | **str**| ID of the notebook to attach | 

### Return type

[**AgenticExperimentSummary**](AgenticExperimentSummary.md)

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

# **create_agentic_experiment_api_v1_tasks_task_id_agentic_experiments_post**
> AgenticExperimentSummary create_agentic_experiment_api_v1_tasks_task_id_agentic_experiments_post(task_id, create_agentic_experiment_request)

Create and run an agentic experiment

Create a new agentic experiment and initiate execution

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_experiment_summary import AgenticExperimentSummary
from _generated.models.create_agentic_experiment_request import CreateAgenticExperimentRequest
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
    api_instance = _generated.AgenticExperimentsApi(api_client)
    task_id = 'task_id_example' # str | 
    create_agentic_experiment_request = _generated.CreateAgenticExperimentRequest() # CreateAgenticExperimentRequest | 

    try:
        # Create and run an agentic experiment
        api_response = api_instance.create_agentic_experiment_api_v1_tasks_task_id_agentic_experiments_post(task_id, create_agentic_experiment_request)
        print("The response of AgenticExperimentsApi->create_agentic_experiment_api_v1_tasks_task_id_agentic_experiments_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticExperimentsApi->create_agentic_experiment_api_v1_tasks_task_id_agentic_experiments_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **create_agentic_experiment_request** | [**CreateAgenticExperimentRequest**](CreateAgenticExperimentRequest.md)|  | 

### Return type

[**AgenticExperimentSummary**](AgenticExperimentSummary.md)

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

# **delete_agentic_experiment_api_v1_agentic_experiments_experiment_id_delete**
> delete_agentic_experiment_api_v1_agentic_experiments_experiment_id_delete(experiment_id)

Delete agentic experiment

Delete an agentic experiment and all its associated data

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
    api_instance = _generated.AgenticExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | The ID of the experiment to delete

    try:
        # Delete agentic experiment
        api_instance.delete_agentic_experiment_api_v1_agentic_experiments_experiment_id_delete(experiment_id)
    except Exception as e:
        print("Exception when calling AgenticExperimentsApi->delete_agentic_experiment_api_v1_agentic_experiments_experiment_id_delete: %s\n" % e)
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

# **get_agentic_experiment_api_v1_agentic_experiments_experiment_id_get**
> AgenticExperimentDetail get_agentic_experiment_api_v1_agentic_experiments_experiment_id_get(experiment_id)

Get agentic experiment details

Get detailed information about a specific agentic experiment including summary results

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_experiment_detail import AgenticExperimentDetail
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
    api_instance = _generated.AgenticExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | The ID of the experiment to retrieve

    try:
        # Get agentic experiment details
        api_response = api_instance.get_agentic_experiment_api_v1_agentic_experiments_experiment_id_get(experiment_id)
        print("The response of AgenticExperimentsApi->get_agentic_experiment_api_v1_agentic_experiments_experiment_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticExperimentsApi->get_agentic_experiment_api_v1_agentic_experiments_experiment_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| The ID of the experiment to retrieve | 

### Return type

[**AgenticExperimentDetail**](AgenticExperimentDetail.md)

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

# **get_agentic_experiment_test_cases_api_v1_agentic_experiments_experiment_id_test_cases_get**
> AgenticTestCaseListResponse get_agentic_experiment_test_cases_api_v1_agentic_experiments_experiment_id_test_cases_get(experiment_id, sort=sort, page_size=page_size, page=page)

Get experiment test cases

Get paginated list of test case results for an agentic experiment

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_test_case_list_response import AgenticTestCaseListResponse
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
    api_instance = _generated.AgenticExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | The ID of the experiment
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get experiment test cases
        api_response = api_instance.get_agentic_experiment_test_cases_api_v1_agentic_experiments_experiment_id_test_cases_get(experiment_id, sort=sort, page_size=page_size, page=page)
        print("The response of AgenticExperimentsApi->get_agentic_experiment_test_cases_api_v1_agentic_experiments_experiment_id_test_cases_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticExperimentsApi->get_agentic_experiment_test_cases_api_v1_agentic_experiments_experiment_id_test_cases_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| The ID of the experiment | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**AgenticTestCaseListResponse**](AgenticTestCaseListResponse.md)

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

# **list_agentic_experiments_api_v1_tasks_task_id_agentic_experiments_get**
> AgenticExperimentListResponse list_agentic_experiments_api_v1_tasks_task_id_agentic_experiments_get(task_id, search=search, dataset_id=dataset_id, sort=sort, page_size=page_size, page=page)

List agentic experiments

List all agentic experiments for a task with optional filtering and pagination

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
    api_instance = _generated.AgenticExperimentsApi(api_client)
    task_id = 'task_id_example' # str | 
    search = 'search_example' # str |  (optional)
    dataset_id = 'dataset_id_example' # str |  (optional)
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # List agentic experiments
        api_response = api_instance.list_agentic_experiments_api_v1_tasks_task_id_agentic_experiments_get(task_id, search=search, dataset_id=dataset_id, sort=sort, page_size=page_size, page=page)
        print("The response of AgenticExperimentsApi->list_agentic_experiments_api_v1_tasks_task_id_agentic_experiments_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgenticExperimentsApi->list_agentic_experiments_api_v1_tasks_task_id_agentic_experiments_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **search** | **str**|  | [optional] 
 **dataset_id** | **str**|  | [optional] 
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

