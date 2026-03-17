# _generated.UsersApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_user_details_api_v1_traces_users_user_id_get**](UsersApi.md#get_user_details_api_v1_traces_users_user_id_get) | **GET** /api/v1/traces/users/{user_id} | Get User Details
[**list_users_metadata_api_v1_traces_users_get**](UsersApi.md#list_users_metadata_api_v1_traces_users_get) | **GET** /api/v1/traces/users | List User Metadata


# **get_user_details_api_v1_traces_users_user_id_get**
> TraceUserMetadataResponse get_user_details_api_v1_traces_users_user_id_get(user_id, task_ids)

Get User Details

Get detailed information for a single user including session and trace metadata.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.trace_user_metadata_response import TraceUserMetadataResponse
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
    api_instance = _generated.UsersApi(api_client)
    user_id = 'user_id_example' # str | 
    task_ids = ['task_ids_example'] # List[str] | Task IDs to filter on. At least one is required.

    try:
        # Get User Details
        api_response = api_instance.get_user_details_api_v1_traces_users_user_id_get(user_id, task_ids)
        print("The response of UsersApi->get_user_details_api_v1_traces_users_user_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling UsersApi->get_user_details_api_v1_traces_users_user_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **user_id** | **str**|  | 
 **task_ids** | [**List[str]**](str.md)| Task IDs to filter on. At least one is required. | 

### Return type

[**TraceUserMetadataResponse**](TraceUserMetadataResponse.md)

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

# **list_users_metadata_api_v1_traces_users_get**
> TraceUserListResponse list_users_metadata_api_v1_traces_users_get(task_ids, start_time=start_time, end_time=end_time, sort=sort, page_size=page_size, page=page)

List User Metadata

Get user metadata with pagination and filtering. Returns aggregated user information across sessions and traces.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.trace_user_list_response import TraceUserListResponse
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
    api_instance = _generated.UsersApi(api_client)
    task_ids = ['task_ids_example'] # List[str] | Task IDs to filter on. At least one is required.
    start_time = '2013-10-20T19:20:30+01:00' # datetime | Inclusive start date in ISO8601 string format. Use local time (not UTC). (optional)
    end_time = '2013-10-20T19:20:30+01:00' # datetime | Exclusive end date in ISO8601 string format. Use local time (not UTC). (optional)
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # List User Metadata
        api_response = api_instance.list_users_metadata_api_v1_traces_users_get(task_ids, start_time=start_time, end_time=end_time, sort=sort, page_size=page_size, page=page)
        print("The response of UsersApi->list_users_metadata_api_v1_traces_users_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling UsersApi->list_users_metadata_api_v1_traces_users_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_ids** | [**List[str]**](str.md)| Task IDs to filter on. At least one is required. | 
 **start_time** | **datetime**| Inclusive start date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **end_time** | **datetime**| Exclusive end date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**TraceUserListResponse**](TraceUserListResponse.md)

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

