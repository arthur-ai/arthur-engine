# arthur_observability_sdk._generated.PromptExperimentsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**attach_notebook_to_experiment_api_v1_prompt_experiments_experiment_id_notebook_patch**](PromptExperimentsApi.md#attach_notebook_to_experiment_api_v1_prompt_experiments_experiment_id_notebook_patch) | **PATCH** /api/v1/prompt_experiments/{experiment_id}/notebook | Attach notebook to experiment
[**create_prompt_experiment_api_v1_tasks_task_id_prompt_experiments_post**](PromptExperimentsApi.md#create_prompt_experiment_api_v1_tasks_task_id_prompt_experiments_post) | **POST** /api/v1/tasks/{task_id}/prompt_experiments | Create and run a prompt experiment
[**delete_prompt_experiment_api_v1_prompt_experiments_experiment_id_delete**](PromptExperimentsApi.md#delete_prompt_experiment_api_v1_prompt_experiments_experiment_id_delete) | **DELETE** /api/v1/prompt_experiments/{experiment_id} | Delete prompt experiment
[**get_experiment_test_cases_api_v1_prompt_experiments_experiment_id_test_cases_get**](PromptExperimentsApi.md#get_experiment_test_cases_api_v1_prompt_experiments_experiment_id_test_cases_get) | **GET** /api/v1/prompt_experiments/{experiment_id}/test_cases | Get experiment test cases
[**get_prompt_experiment_api_v1_prompt_experiments_experiment_id_get**](PromptExperimentsApi.md#get_prompt_experiment_api_v1_prompt_experiments_experiment_id_get) | **GET** /api/v1/prompt_experiments/{experiment_id} | Get prompt experiment details
[**get_prompt_version_results_api_v1_prompt_experiments_experiment_id_prompts_prompt_key_results_get**](PromptExperimentsApi.md#get_prompt_version_results_api_v1_prompt_experiments_experiment_id_prompts_prompt_key_results_get) | **GET** /api/v1/prompt_experiments/{experiment_id}/prompts/{prompt_key}/results | Get prompt results
[**list_prompt_experiments_api_v1_tasks_task_id_prompt_experiments_get**](PromptExperimentsApi.md#list_prompt_experiments_api_v1_tasks_task_id_prompt_experiments_get) | **GET** /api/v1/tasks/{task_id}/prompt_experiments | List prompt experiments


# **attach_notebook_to_experiment_api_v1_prompt_experiments_experiment_id_notebook_patch**
> PromptExperimentSummary attach_notebook_to_experiment_api_v1_prompt_experiments_experiment_id_notebook_patch(experiment_id, notebook_id)

Attach notebook to experiment

Attach a notebook to an existing experiment

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.prompt_experiment_summary import PromptExperimentSummary
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
    api_instance = arthur_observability_sdk._generated.PromptExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | ID of the experiment
    notebook_id = 'notebook_id_example' # str | ID of the notebook to attach

    try:
        # Attach notebook to experiment
        api_response = api_instance.attach_notebook_to_experiment_api_v1_prompt_experiments_experiment_id_notebook_patch(experiment_id, notebook_id)
        print("The response of PromptExperimentsApi->attach_notebook_to_experiment_api_v1_prompt_experiments_experiment_id_notebook_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptExperimentsApi->attach_notebook_to_experiment_api_v1_prompt_experiments_experiment_id_notebook_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| ID of the experiment | 
 **notebook_id** | **str**| ID of the notebook to attach | 

### Return type

[**PromptExperimentSummary**](PromptExperimentSummary.md)

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

# **create_prompt_experiment_api_v1_tasks_task_id_prompt_experiments_post**
> PromptExperimentSummary create_prompt_experiment_api_v1_tasks_task_id_prompt_experiments_post(task_id, create_prompt_experiment_request)

Create and run a prompt experiment

Create a new prompt experiment and initiate execution

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.create_prompt_experiment_request import CreatePromptExperimentRequest
from arthur_observability_sdk._generated.models.prompt_experiment_summary import PromptExperimentSummary
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
    api_instance = arthur_observability_sdk._generated.PromptExperimentsApi(api_client)
    task_id = 'task_id_example' # str | 
    create_prompt_experiment_request = arthur_observability_sdk._generated.CreatePromptExperimentRequest() # CreatePromptExperimentRequest | 

    try:
        # Create and run a prompt experiment
        api_response = api_instance.create_prompt_experiment_api_v1_tasks_task_id_prompt_experiments_post(task_id, create_prompt_experiment_request)
        print("The response of PromptExperimentsApi->create_prompt_experiment_api_v1_tasks_task_id_prompt_experiments_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptExperimentsApi->create_prompt_experiment_api_v1_tasks_task_id_prompt_experiments_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **create_prompt_experiment_request** | [**CreatePromptExperimentRequest**](CreatePromptExperimentRequest.md)|  | 

### Return type

[**PromptExperimentSummary**](PromptExperimentSummary.md)

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

# **delete_prompt_experiment_api_v1_prompt_experiments_experiment_id_delete**
> delete_prompt_experiment_api_v1_prompt_experiments_experiment_id_delete(experiment_id)

Delete prompt experiment

Delete a prompt experiment and all its associated data

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
    api_instance = arthur_observability_sdk._generated.PromptExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | The ID of the experiment to delete

    try:
        # Delete prompt experiment
        api_instance.delete_prompt_experiment_api_v1_prompt_experiments_experiment_id_delete(experiment_id)
    except Exception as e:
        print("Exception when calling PromptExperimentsApi->delete_prompt_experiment_api_v1_prompt_experiments_experiment_id_delete: %s\n" % e)
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

# **get_experiment_test_cases_api_v1_prompt_experiments_experiment_id_test_cases_get**
> TestCaseListResponse get_experiment_test_cases_api_v1_prompt_experiments_experiment_id_test_cases_get(experiment_id, sort=sort, page_size=page_size, page=page)

Get experiment test cases

Get paginated list of test case results for a prompt experiment

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.test_case_list_response import TestCaseListResponse
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
    api_instance = arthur_observability_sdk._generated.PromptExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | The ID of the experiment
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get experiment test cases
        api_response = api_instance.get_experiment_test_cases_api_v1_prompt_experiments_experiment_id_test_cases_get(experiment_id, sort=sort, page_size=page_size, page=page)
        print("The response of PromptExperimentsApi->get_experiment_test_cases_api_v1_prompt_experiments_experiment_id_test_cases_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptExperimentsApi->get_experiment_test_cases_api_v1_prompt_experiments_experiment_id_test_cases_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| The ID of the experiment | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**TestCaseListResponse**](TestCaseListResponse.md)

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

# **get_prompt_experiment_api_v1_prompt_experiments_experiment_id_get**
> PromptExperimentDetail get_prompt_experiment_api_v1_prompt_experiments_experiment_id_get(experiment_id)

Get prompt experiment details

Get detailed information about a specific prompt experiment including summary results

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.prompt_experiment_detail import PromptExperimentDetail
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
    api_instance = arthur_observability_sdk._generated.PromptExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | The ID of the experiment to retrieve

    try:
        # Get prompt experiment details
        api_response = api_instance.get_prompt_experiment_api_v1_prompt_experiments_experiment_id_get(experiment_id)
        print("The response of PromptExperimentsApi->get_prompt_experiment_api_v1_prompt_experiments_experiment_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptExperimentsApi->get_prompt_experiment_api_v1_prompt_experiments_experiment_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| The ID of the experiment to retrieve | 

### Return type

[**PromptExperimentDetail**](PromptExperimentDetail.md)

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

# **get_prompt_version_results_api_v1_prompt_experiments_experiment_id_prompts_prompt_key_results_get**
> PromptVersionResultListResponse get_prompt_version_results_api_v1_prompt_experiments_experiment_id_prompts_prompt_key_results_get(experiment_id, prompt_key, sort=sort, page_size=page_size, page=page)

Get prompt results

Get paginated list of results for a specific prompt within an experiment (supports both saved and unsaved prompts)

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.prompt_version_result_list_response import PromptVersionResultListResponse
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
    api_instance = arthur_observability_sdk._generated.PromptExperimentsApi(api_client)
    experiment_id = 'experiment_id_example' # str | The ID of the experiment
    prompt_key = 'prompt_key_example' # str | The prompt key (format: 'saved:name:version' or 'unsaved:auto_name'). URL-encode colons as %3A
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get prompt results
        api_response = api_instance.get_prompt_version_results_api_v1_prompt_experiments_experiment_id_prompts_prompt_key_results_get(experiment_id, prompt_key, sort=sort, page_size=page_size, page=page)
        print("The response of PromptExperimentsApi->get_prompt_version_results_api_v1_prompt_experiments_experiment_id_prompts_prompt_key_results_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptExperimentsApi->get_prompt_version_results_api_v1_prompt_experiments_experiment_id_prompts_prompt_key_results_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **experiment_id** | **str**| The ID of the experiment | 
 **prompt_key** | **str**| The prompt key (format: &#39;saved:name:version&#39; or &#39;unsaved:auto_name&#39;). URL-encode colons as %3A | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**PromptVersionResultListResponse**](PromptVersionResultListResponse.md)

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

# **list_prompt_experiments_api_v1_tasks_task_id_prompt_experiments_get**
> PromptExperimentListResponse list_prompt_experiments_api_v1_tasks_task_id_prompt_experiments_get(task_id, search=search, dataset_id=dataset_id, sort=sort, page_size=page_size, page=page)

List prompt experiments

List all prompt experiments for a task with optional filtering and pagination

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.prompt_experiment_list_response import PromptExperimentListResponse
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
    api_instance = arthur_observability_sdk._generated.PromptExperimentsApi(api_client)
    task_id = 'task_id_example' # str | 
    search = 'search_example' # str | Search text to filter experiments by name, description, prompt name, or dataset name (optional)
    dataset_id = 'dataset_id_example' # str | Filter experiments by dataset ID (optional)
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # List prompt experiments
        api_response = api_instance.list_prompt_experiments_api_v1_tasks_task_id_prompt_experiments_get(task_id, search=search, dataset_id=dataset_id, sort=sort, page_size=page_size, page=page)
        print("The response of PromptExperimentsApi->list_prompt_experiments_api_v1_tasks_task_id_prompt_experiments_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptExperimentsApi->list_prompt_experiments_api_v1_tasks_task_id_prompt_experiments_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **search** | **str**| Search text to filter experiments by name, description, prompt name, or dataset name | [optional] 
 **dataset_id** | **str**| Filter experiments by dataset ID | [optional] 
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

