# _generated.SessionsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**compute_session_metrics_api_v1_traces_sessions_session_id_metrics_get**](SessionsApi.md#compute_session_metrics_api_v1_traces_sessions_session_id_metrics_get) | **GET** /api/v1/traces/sessions/{session_id}/metrics | Compute Missing Session Metrics
[**get_session_traces_api_v1_traces_sessions_session_id_get**](SessionsApi.md#get_session_traces_api_v1_traces_sessions_session_id_get) | **GET** /api/v1/traces/sessions/{session_id} | Get Session Traces
[**list_sessions_metadata_api_v1_traces_sessions_get**](SessionsApi.md#list_sessions_metadata_api_v1_traces_sessions_get) | **GET** /api/v1/traces/sessions | List Session Metadata


# **compute_session_metrics_api_v1_traces_sessions_session_id_metrics_get**
> SessionTracesResponse compute_session_metrics_api_v1_traces_sessions_session_id_metrics_get(session_id, sort=sort, page_size=page_size, page=page)

Compute Missing Session Metrics

Get all traces in a session and compute missing metrics. Returns list of full trace trees with computed metrics.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.session_traces_response import SessionTracesResponse
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
    api_instance = _generated.SessionsApi(api_client)
    session_id = 'session_id_example' # str | 
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Compute Missing Session Metrics
        api_response = api_instance.compute_session_metrics_api_v1_traces_sessions_session_id_metrics_get(session_id, sort=sort, page_size=page_size, page=page)
        print("The response of SessionsApi->compute_session_metrics_api_v1_traces_sessions_session_id_metrics_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SessionsApi->compute_session_metrics_api_v1_traces_sessions_session_id_metrics_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **str**|  | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**SessionTracesResponse**](SessionTracesResponse.md)

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

# **get_session_traces_api_v1_traces_sessions_session_id_get**
> SessionTracesResponse get_session_traces_api_v1_traces_sessions_session_id_get(session_id, sort=sort, page_size=page_size, page=page)

Get Session Traces

Get all traces in a session. Returns list of full trace trees with existing metrics (no computation).

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.session_traces_response import SessionTracesResponse
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
    api_instance = _generated.SessionsApi(api_client)
    session_id = 'session_id_example' # str | 
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get Session Traces
        api_response = api_instance.get_session_traces_api_v1_traces_sessions_session_id_get(session_id, sort=sort, page_size=page_size, page=page)
        print("The response of SessionsApi->get_session_traces_api_v1_traces_sessions_session_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SessionsApi->get_session_traces_api_v1_traces_sessions_session_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **session_id** | **str**|  | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**SessionTracesResponse**](SessionTracesResponse.md)

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

# **list_sessions_metadata_api_v1_traces_sessions_get**
> SessionListResponse list_sessions_metadata_api_v1_traces_sessions_get(task_ids, start_time=start_time, end_time=end_time, user_ids=user_ids, include_experiment_sessions=include_experiment_sessions, sort=sort, page_size=page_size, page=page)

List Session Metadata

Get session metadata with pagination and filtering. Returns aggregated session information.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.session_list_response import SessionListResponse
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
    api_instance = _generated.SessionsApi(api_client)
    task_ids = ['task_ids_example'] # List[str] | Task IDs to filter on. At least one is required.
    start_time = '2013-10-20T19:20:30+01:00' # datetime | Inclusive start date in ISO8601 string format. Use local time (not UTC). (optional)
    end_time = '2013-10-20T19:20:30+01:00' # datetime | Exclusive end date in ISO8601 string format. Use local time (not UTC). (optional)
    user_ids = ['user_ids_example'] # List[str] | User IDs to filter on. Optional. (optional)
    include_experiment_sessions = False # bool | Include sessions originating from Arthur experiments. Defaults to false for most uses. (optional) (default to False)
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # List Session Metadata
        api_response = api_instance.list_sessions_metadata_api_v1_traces_sessions_get(task_ids, start_time=start_time, end_time=end_time, user_ids=user_ids, include_experiment_sessions=include_experiment_sessions, sort=sort, page_size=page_size, page=page)
        print("The response of SessionsApi->list_sessions_metadata_api_v1_traces_sessions_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SessionsApi->list_sessions_metadata_api_v1_traces_sessions_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_ids** | [**List[str]**](str.md)| Task IDs to filter on. At least one is required. | 
 **start_time** | **datetime**| Inclusive start date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **end_time** | **datetime**| Exclusive end date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **user_ids** | [**List[str]**](str.md)| User IDs to filter on. Optional. | [optional] 
 **include_experiment_sessions** | **bool**| Include sessions originating from Arthur experiments. Defaults to false for most uses. | [optional] [default to False]
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**SessionListResponse**](SessionListResponse.md)

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

