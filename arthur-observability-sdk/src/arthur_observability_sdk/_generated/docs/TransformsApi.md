# arthur_observability_sdk._generated.TransformsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_transform_for_task_api_v1_tasks_task_id_traces_transforms_post**](TransformsApi.md#create_transform_for_task_api_v1_tasks_task_id_traces_transforms_post) | **POST** /api/v1/tasks/{task_id}/traces/transforms | Create Transform For Task
[**delete_transform_api_v1_traces_transforms_transform_id_delete**](TransformsApi.md#delete_transform_api_v1_traces_transforms_transform_id_delete) | **DELETE** /api/v1/traces/transforms/{transform_id} | Delete Transform
[**execute_trace_transform_extraction_api_v1_traces_trace_id_transforms_transform_id_extractions_post**](TransformsApi.md#execute_trace_transform_extraction_api_v1_traces_trace_id_transforms_transform_id_extractions_post) | **POST** /api/v1/traces/{trace_id}/transforms/{transform_id}/extractions | Execute Trace Transform Extraction
[**get_transform_api_v1_traces_transforms_transform_id_get**](TransformsApi.md#get_transform_api_v1_traces_transforms_transform_id_get) | **GET** /api/v1/traces/transforms/{transform_id} | Get Transform
[**list_transforms_for_task_api_v1_tasks_task_id_traces_transforms_get**](TransformsApi.md#list_transforms_for_task_api_v1_tasks_task_id_traces_transforms_get) | **GET** /api/v1/tasks/{task_id}/traces/transforms | List Transforms For Task
[**update_transform_api_v1_traces_transforms_transform_id_patch**](TransformsApi.md#update_transform_api_v1_traces_transforms_transform_id_patch) | **PATCH** /api/v1/traces/transforms/{transform_id} | Update Transform


# **create_transform_for_task_api_v1_tasks_task_id_traces_transforms_post**
> TraceTransformResponse create_transform_for_task_api_v1_tasks_task_id_traces_transforms_post(task_id, new_trace_transform_request)

Create Transform For Task

Create a new transform for a task.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.new_trace_transform_request import NewTraceTransformRequest
from arthur_observability_sdk._generated.models.trace_transform_response import TraceTransformResponse
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
    api_instance = arthur_observability_sdk._generated.TransformsApi(api_client)
    task_id = 'task_id_example' # str | 
    new_trace_transform_request = arthur_observability_sdk._generated.NewTraceTransformRequest() # NewTraceTransformRequest | 

    try:
        # Create Transform For Task
        api_response = api_instance.create_transform_for_task_api_v1_tasks_task_id_traces_transforms_post(task_id, new_trace_transform_request)
        print("The response of TransformsApi->create_transform_for_task_api_v1_tasks_task_id_traces_transforms_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TransformsApi->create_transform_for_task_api_v1_tasks_task_id_traces_transforms_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **new_trace_transform_request** | [**NewTraceTransformRequest**](NewTraceTransformRequest.md)|  | 

### Return type

[**TraceTransformResponse**](TraceTransformResponse.md)

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

# **delete_transform_api_v1_traces_transforms_transform_id_delete**
> delete_transform_api_v1_traces_transforms_transform_id_delete(transform_id)

Delete Transform

Delete a transform.

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
    api_instance = arthur_observability_sdk._generated.TransformsApi(api_client)
    transform_id = 'transform_id_example' # str | ID of the transform to delete.

    try:
        # Delete Transform
        api_instance.delete_transform_api_v1_traces_transforms_transform_id_delete(transform_id)
    except Exception as e:
        print("Exception when calling TransformsApi->delete_transform_api_v1_traces_transforms_transform_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **transform_id** | **str**| ID of the transform to delete. | 

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

# **execute_trace_transform_extraction_api_v1_traces_trace_id_transforms_transform_id_extractions_post**
> TransformExtractionResponseList execute_trace_transform_extraction_api_v1_traces_trace_id_transforms_transform_id_extractions_post(trace_id, transform_id)

Execute Trace Transform Extraction

Execute a transform against a trace to extract variables.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.transform_extraction_response_list import TransformExtractionResponseList
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
    api_instance = arthur_observability_sdk._generated.TransformsApi(api_client)
    trace_id = 'trace_id_example' # str | ID of the trace to execute the transform against.
    transform_id = 'transform_id_example' # str | ID of the transform to execute.

    try:
        # Execute Trace Transform Extraction
        api_response = api_instance.execute_trace_transform_extraction_api_v1_traces_trace_id_transforms_transform_id_extractions_post(trace_id, transform_id)
        print("The response of TransformsApi->execute_trace_transform_extraction_api_v1_traces_trace_id_transforms_transform_id_extractions_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TransformsApi->execute_trace_transform_extraction_api_v1_traces_trace_id_transforms_transform_id_extractions_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **trace_id** | **str**| ID of the trace to execute the transform against. | 
 **transform_id** | **str**| ID of the transform to execute. | 

### Return type

[**TransformExtractionResponseList**](TransformExtractionResponseList.md)

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

# **get_transform_api_v1_traces_transforms_transform_id_get**
> TraceTransformResponse get_transform_api_v1_traces_transforms_transform_id_get(transform_id)

Get Transform

Get a specific transform.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.trace_transform_response import TraceTransformResponse
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
    api_instance = arthur_observability_sdk._generated.TransformsApi(api_client)
    transform_id = 'transform_id_example' # str | ID of the transform to fetch.

    try:
        # Get Transform
        api_response = api_instance.get_transform_api_v1_traces_transforms_transform_id_get(transform_id)
        print("The response of TransformsApi->get_transform_api_v1_traces_transforms_transform_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TransformsApi->get_transform_api_v1_traces_transforms_transform_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **transform_id** | **str**| ID of the transform to fetch. | 

### Return type

[**TraceTransformResponse**](TraceTransformResponse.md)

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

# **list_transforms_for_task_api_v1_tasks_task_id_traces_transforms_get**
> ListTraceTransformsResponse list_transforms_for_task_api_v1_tasks_task_id_traces_transforms_get(task_id, sort=sort, page_size=page_size, page=page, name=name, created_after=created_after, created_before=created_before)

List Transforms For Task

List all transforms for a task.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.list_trace_transforms_response import ListTraceTransformsResponse
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
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
    api_instance = arthur_observability_sdk._generated.TransformsApi(api_client)
    task_id = 'task_id_example' # str | 
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)
    name = 'name_example' # str | Name of the transform to filter on using partial matching. (optional)
    created_after = 'created_after_example' # str | Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC). (optional)
    created_before = 'created_before_example' # str | Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC). (optional)

    try:
        # List Transforms For Task
        api_response = api_instance.list_transforms_for_task_api_v1_tasks_task_id_traces_transforms_get(task_id, sort=sort, page_size=page_size, page=page, name=name, created_after=created_after, created_before=created_before)
        print("The response of TransformsApi->list_transforms_for_task_api_v1_tasks_task_id_traces_transforms_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TransformsApi->list_transforms_for_task_api_v1_tasks_task_id_traces_transforms_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]
 **name** | **str**| Name of the transform to filter on using partial matching. | [optional] 
 **created_after** | **str**| Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC). | [optional] 
 **created_before** | **str**| Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC). | [optional] 

### Return type

[**ListTraceTransformsResponse**](ListTraceTransformsResponse.md)

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

# **update_transform_api_v1_traces_transforms_transform_id_patch**
> TraceTransformResponse update_transform_api_v1_traces_transforms_transform_id_patch(transform_id, trace_transform_update_request)

Update Transform

Update a transform.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.trace_transform_response import TraceTransformResponse
from arthur_observability_sdk._generated.models.trace_transform_update_request import TraceTransformUpdateRequest
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
    api_instance = arthur_observability_sdk._generated.TransformsApi(api_client)
    transform_id = 'transform_id_example' # str | ID of the transform to update.
    trace_transform_update_request = arthur_observability_sdk._generated.TraceTransformUpdateRequest() # TraceTransformUpdateRequest | 

    try:
        # Update Transform
        api_response = api_instance.update_transform_api_v1_traces_transforms_transform_id_patch(transform_id, trace_transform_update_request)
        print("The response of TransformsApi->update_transform_api_v1_traces_transforms_transform_id_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TransformsApi->update_transform_api_v1_traces_transforms_transform_id_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **transform_id** | **str**| ID of the transform to update. | 
 **trace_transform_update_request** | [**TraceTransformUpdateRequest**](TraceTransformUpdateRequest.md)|  | 

### Return type

[**TraceTransformResponse**](TraceTransformResponse.md)

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

