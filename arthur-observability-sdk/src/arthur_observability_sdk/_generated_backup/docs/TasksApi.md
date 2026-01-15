# _generated.TasksApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**archive_task_api_v2_tasks_task_id_delete**](TasksApi.md#archive_task_api_v2_tasks_task_id_delete) | **DELETE** /api/v2/tasks/{task_id} | Archive Task
[**archive_task_metric_api_v2_tasks_task_id_metrics_metric_id_delete**](TasksApi.md#archive_task_metric_api_v2_tasks_task_id_metrics_metric_id_delete) | **DELETE** /api/v2/tasks/{task_id}/metrics/{metric_id} | Archive Task Metric
[**archive_task_rule_api_v2_tasks_task_id_rules_rule_id_delete**](TasksApi.md#archive_task_rule_api_v2_tasks_task_id_rules_rule_id_delete) | **DELETE** /api/v2/tasks/{task_id}/rules/{rule_id} | Archive Task Rule
[**create_task_api_v2_tasks_post**](TasksApi.md#create_task_api_v2_tasks_post) | **POST** /api/v2/tasks | Create Task
[**create_task_metric_api_v2_tasks_task_id_metrics_post**](TasksApi.md#create_task_metric_api_v2_tasks_task_id_metrics_post) | **POST** /api/v2/tasks/{task_id}/metrics | Create Task Metric
[**create_task_rule_api_v2_tasks_task_id_rules_post**](TasksApi.md#create_task_rule_api_v2_tasks_task_id_rules_post) | **POST** /api/v2/tasks/{task_id}/rules | Create Task Rule
[**get_all_tasks_api_v2_tasks_get**](TasksApi.md#get_all_tasks_api_v2_tasks_get) | **GET** /api/v2/tasks | Get All Tasks
[**get_task_api_v2_tasks_task_id_get**](TasksApi.md#get_task_api_v2_tasks_task_id_get) | **GET** /api/v2/tasks/{task_id} | Get Task
[**redirect_to_tasks_api_v2_task_post**](TasksApi.md#redirect_to_tasks_api_v2_task_post) | **POST** /api/v2/task | Redirect To Tasks
[**search_tasks_api_v2_tasks_search_post**](TasksApi.md#search_tasks_api_v2_tasks_search_post) | **POST** /api/v2/tasks/search | Search Tasks
[**update_task_metric_api_v2_tasks_task_id_metrics_metric_id_patch**](TasksApi.md#update_task_metric_api_v2_tasks_task_id_metrics_metric_id_patch) | **PATCH** /api/v2/tasks/{task_id}/metrics/{metric_id} | Update Task Metric
[**update_task_rules_api_v2_tasks_task_id_rules_rule_id_patch**](TasksApi.md#update_task_rules_api_v2_tasks_task_id_rules_rule_id_patch) | **PATCH** /api/v2/tasks/{task_id}/rules/{rule_id} | Update Task Rules


# **archive_task_api_v2_tasks_task_id_delete**
> object archive_task_api_v2_tasks_task_id_delete(task_id)

Archive Task

Archive task. Also archives all task-scoped rules. Associated default rules are unaffected.

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
    api_instance = _generated.TasksApi(api_client)
    task_id = 'task_id_example' # str | 

    try:
        # Archive Task
        api_response = api_instance.archive_task_api_v2_tasks_task_id_delete(task_id)
        print("The response of TasksApi->archive_task_api_v2_tasks_task_id_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->archive_task_api_v2_tasks_task_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 

### Return type

**object**

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

# **archive_task_metric_api_v2_tasks_task_id_metrics_metric_id_delete**
> object archive_task_metric_api_v2_tasks_task_id_metrics_metric_id_delete(task_id, metric_id)

Archive Task Metric

Archive a task metric.

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
    api_instance = _generated.TasksApi(api_client)
    task_id = 'task_id_example' # str | 
    metric_id = 'metric_id_example' # str | 

    try:
        # Archive Task Metric
        api_response = api_instance.archive_task_metric_api_v2_tasks_task_id_metrics_metric_id_delete(task_id, metric_id)
        print("The response of TasksApi->archive_task_metric_api_v2_tasks_task_id_metrics_metric_id_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->archive_task_metric_api_v2_tasks_task_id_metrics_metric_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **metric_id** | **str**|  | 

### Return type

**object**

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

# **archive_task_rule_api_v2_tasks_task_id_rules_rule_id_delete**
> object archive_task_rule_api_v2_tasks_task_id_rules_rule_id_delete(task_id, rule_id)

Archive Task Rule

Archive an existing rule for this task.

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
    api_instance = _generated.TasksApi(api_client)
    task_id = 'task_id_example' # str | 
    rule_id = 'rule_id_example' # str | 

    try:
        # Archive Task Rule
        api_response = api_instance.archive_task_rule_api_v2_tasks_task_id_rules_rule_id_delete(task_id, rule_id)
        print("The response of TasksApi->archive_task_rule_api_v2_tasks_task_id_rules_rule_id_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->archive_task_rule_api_v2_tasks_task_id_rules_rule_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **rule_id** | **str**|  | 

### Return type

**object**

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

# **create_task_api_v2_tasks_post**
> TaskResponse create_task_api_v2_tasks_post(new_task_request)

Create Task

Register a new task. When a new task is created, all existing default rules will be auto-applied for this new task. Optionally specify if the task is agentic.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.new_task_request import NewTaskRequest
from _generated.models.task_response import TaskResponse
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
    api_instance = _generated.TasksApi(api_client)
    new_task_request = _generated.NewTaskRequest() # NewTaskRequest | 

    try:
        # Create Task
        api_response = api_instance.create_task_api_v2_tasks_post(new_task_request)
        print("The response of TasksApi->create_task_api_v2_tasks_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->create_task_api_v2_tasks_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **new_task_request** | [**NewTaskRequest**](NewTaskRequest.md)|  | 

### Return type

[**TaskResponse**](TaskResponse.md)

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

# **create_task_metric_api_v2_tasks_task_id_metrics_post**
> MetricResponse create_task_metric_api_v2_tasks_task_id_metrics_post(task_id, new_metric_request=new_metric_request)

Create Task Metric

Create metrics for a task. Only agentic tasks can have metrics.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.metric_response import MetricResponse
from _generated.models.new_metric_request import NewMetricRequest
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
    api_instance = _generated.TasksApi(api_client)
    task_id = 'task_id_example' # str | 
    new_metric_request = _generated.NewMetricRequest() # NewMetricRequest |  (optional)

    try:
        # Create Task Metric
        api_response = api_instance.create_task_metric_api_v2_tasks_task_id_metrics_post(task_id, new_metric_request=new_metric_request)
        print("The response of TasksApi->create_task_metric_api_v2_tasks_task_id_metrics_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->create_task_metric_api_v2_tasks_task_id_metrics_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **new_metric_request** | [**NewMetricRequest**](NewMetricRequest.md)|  | [optional] 

### Return type

[**MetricResponse**](MetricResponse.md)

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

# **create_task_rule_api_v2_tasks_task_id_rules_post**
> RuleResponse create_task_rule_api_v2_tasks_task_id_rules_post(task_id, new_rule_request=new_rule_request)

Create Task Rule

Create a rule to be applied only to this task. Available rule types are KeywordRule, ModelHallucinationRuleV2, ModelSensitiveDataRule, PIIDataRule, PromptInjectionRule, RegexRule, ToxicityRule.Note: The rules are cached by the validation endpoints for 60 seconds.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.new_rule_request import NewRuleRequest
from _generated.models.rule_response import RuleResponse
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
    api_instance = _generated.TasksApi(api_client)
    task_id = 'task_id_example' # str | 
    new_rule_request = {name=Sensitive Data Rule, type=ModelSensitiveDataRule, apply_to_prompt=true, apply_to_response=false, config={examples=[{example=John has O negative blood group, result=true}, {example=Most of the people have A positive blood group, result=false}], hint=specific individual's blood types}} # NewRuleRequest |  (optional)

    try:
        # Create Task Rule
        api_response = api_instance.create_task_rule_api_v2_tasks_task_id_rules_post(task_id, new_rule_request=new_rule_request)
        print("The response of TasksApi->create_task_rule_api_v2_tasks_task_id_rules_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->create_task_rule_api_v2_tasks_task_id_rules_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **new_rule_request** | [**NewRuleRequest**](NewRuleRequest.md)|  | [optional] 

### Return type

[**RuleResponse**](RuleResponse.md)

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

# **get_all_tasks_api_v2_tasks_get**
> List[TaskResponse] get_all_tasks_api_v2_tasks_get()

Get All Tasks

[Deprecated] Use /tasks/search endpoint. This endpoint will be removed in a future release.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.task_response import TaskResponse
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
    api_instance = _generated.TasksApi(api_client)

    try:
        # Get All Tasks
        api_response = api_instance.get_all_tasks_api_v2_tasks_get()
        print("The response of TasksApi->get_all_tasks_api_v2_tasks_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->get_all_tasks_api_v2_tasks_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**List[TaskResponse]**](TaskResponse.md)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_task_api_v2_tasks_task_id_get**
> TaskResponse get_task_api_v2_tasks_task_id_get(task_id)

Get Task

Get tasks.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.task_response import TaskResponse
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
    api_instance = _generated.TasksApi(api_client)
    task_id = 'task_id_example' # str | 

    try:
        # Get Task
        api_response = api_instance.get_task_api_v2_tasks_task_id_get(task_id)
        print("The response of TasksApi->get_task_api_v2_tasks_task_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->get_task_api_v2_tasks_task_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 

### Return type

[**TaskResponse**](TaskResponse.md)

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

# **redirect_to_tasks_api_v2_task_post**
> object redirect_to_tasks_api_v2_task_post()

Redirect To Tasks

Redirect to /tasks endpoint.

### Example


```python
import _generated
from _generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = _generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with _generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = _generated.TasksApi(api_client)

    try:
        # Redirect To Tasks
        api_response = api_instance.redirect_to_tasks_api_v2_task_post()
        print("The response of TasksApi->redirect_to_tasks_api_v2_task_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->redirect_to_tasks_api_v2_task_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

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

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **search_tasks_api_v2_tasks_search_post**
> SearchTasksResponse search_tasks_api_v2_tasks_search_post(search_tasks_request, sort=sort, page_size=page_size, page=page)

Search Tasks

Search tasks. Can filter by task IDs, task name substring, and agentic status.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.search_tasks_request import SearchTasksRequest
from _generated.models.search_tasks_response import SearchTasksResponse
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
    api_instance = _generated.TasksApi(api_client)
    search_tasks_request = _generated.SearchTasksRequest() # SearchTasksRequest | 
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Search Tasks
        api_response = api_instance.search_tasks_api_v2_tasks_search_post(search_tasks_request, sort=sort, page_size=page_size, page=page)
        print("The response of TasksApi->search_tasks_api_v2_tasks_search_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->search_tasks_api_v2_tasks_search_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **search_tasks_request** | [**SearchTasksRequest**](SearchTasksRequest.md)|  | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**SearchTasksResponse**](SearchTasksResponse.md)

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

# **update_task_metric_api_v2_tasks_task_id_metrics_metric_id_patch**
> TaskResponse update_task_metric_api_v2_tasks_task_id_metrics_metric_id_patch(task_id, metric_id, update_metric_request)

Update Task Metric

Update a task metric.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.task_response import TaskResponse
from _generated.models.update_metric_request import UpdateMetricRequest
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
    api_instance = _generated.TasksApi(api_client)
    task_id = 'task_id_example' # str | 
    metric_id = 'metric_id_example' # str | 
    update_metric_request = _generated.UpdateMetricRequest() # UpdateMetricRequest | 

    try:
        # Update Task Metric
        api_response = api_instance.update_task_metric_api_v2_tasks_task_id_metrics_metric_id_patch(task_id, metric_id, update_metric_request)
        print("The response of TasksApi->update_task_metric_api_v2_tasks_task_id_metrics_metric_id_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->update_task_metric_api_v2_tasks_task_id_metrics_metric_id_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **metric_id** | **str**|  | 
 **update_metric_request** | [**UpdateMetricRequest**](UpdateMetricRequest.md)|  | 

### Return type

[**TaskResponse**](TaskResponse.md)

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

# **update_task_rules_api_v2_tasks_task_id_rules_rule_id_patch**
> TaskResponse update_task_rules_api_v2_tasks_task_id_rules_rule_id_patch(task_id, rule_id, update_rule_request)

Update Task Rules

Enable or disable an existing rule for this task including the default rules.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.task_response import TaskResponse
from _generated.models.update_rule_request import UpdateRuleRequest
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
    api_instance = _generated.TasksApi(api_client)
    task_id = 'task_id_example' # str | 
    rule_id = 'rule_id_example' # str | 
    update_rule_request = _generated.UpdateRuleRequest() # UpdateRuleRequest | 

    try:
        # Update Task Rules
        api_response = api_instance.update_task_rules_api_v2_tasks_task_id_rules_rule_id_patch(task_id, rule_id, update_rule_request)
        print("The response of TasksApi->update_task_rules_api_v2_tasks_task_id_rules_rule_id_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TasksApi->update_task_rules_api_v2_tasks_task_id_rules_rule_id_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **rule_id** | **str**|  | 
 **update_rule_request** | [**UpdateRuleRequest**](UpdateRuleRequest.md)|  | 

### Return type

[**TaskResponse**](TaskResponse.md)

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

