# arthur_observability_sdk._generated.TracesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**annotate_trace_api_v1_traces_trace_id_annotations_post**](TracesApi.md#annotate_trace_api_v1_traces_trace_id_annotations_post) | **POST** /api/v1/traces/{trace_id}/annotations | Annotate a Trace
[**compute_trace_metrics_api_v1_traces_trace_id_metrics_get**](TracesApi.md#compute_trace_metrics_api_v1_traces_trace_id_metrics_get) | **GET** /api/v1/traces/{trace_id}/metrics | Compute Missing Trace Metrics
[**delete_annotation_from_trace_api_v1_traces_trace_id_annotations_delete**](TracesApi.md#delete_annotation_from_trace_api_v1_traces_trace_id_annotations_delete) | **DELETE** /api/v1/traces/{trace_id}/annotations | Delete an annotation from a trace
[**get_annotation_by_id_api_v1_traces_annotations_annotation_id_get**](TracesApi.md#get_annotation_by_id_api_v1_traces_annotations_annotation_id_get) | **GET** /api/v1/traces/annotations/{annotation_id} | Get an annotation by id
[**get_trace_by_id_api_v1_traces_trace_id_get**](TracesApi.md#get_trace_by_id_api_v1_traces_trace_id_get) | **GET** /api/v1/traces/{trace_id} | Get Single Trace
[**list_annotations_for_trace_api_v1_traces_trace_id_annotations_get**](TracesApi.md#list_annotations_for_trace_api_v1_traces_trace_id_annotations_get) | **GET** /api/v1/traces/{trace_id}/annotations | List Annotations for a Trace
[**list_traces_metadata_api_v1_traces_get**](TracesApi.md#list_traces_metadata_api_v1_traces_get) | **GET** /api/v1/traces | List Trace Metadata
[**receive_traces_api_v1_traces_post**](TracesApi.md#receive_traces_api_v1_traces_post) | **POST** /api/v1/traces | Receive Traces
[**receive_traces_v1_traces_post**](TracesApi.md#receive_traces_v1_traces_post) | **POST** /v1/traces | Receive Traces


# **annotate_trace_api_v1_traces_trace_id_annotations_post**
> AgenticAnnotationResponse annotate_trace_api_v1_traces_trace_id_annotations_post(trace_id, agentic_annotation_request)

Annotate a Trace

Annotate a trace with a score and description (1 = liked, 0 = disliked)

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.agentic_annotation_request import AgenticAnnotationRequest
from arthur_observability_sdk._generated.models.agentic_annotation_response import AgenticAnnotationResponse
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
    api_instance = arthur_observability_sdk._generated.TracesApi(api_client)
    trace_id = 'trace_id_example' # str | 
    agentic_annotation_request = arthur_observability_sdk._generated.AgenticAnnotationRequest() # AgenticAnnotationRequest | 

    try:
        # Annotate a Trace
        api_response = api_instance.annotate_trace_api_v1_traces_trace_id_annotations_post(trace_id, agentic_annotation_request)
        print("The response of TracesApi->annotate_trace_api_v1_traces_trace_id_annotations_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TracesApi->annotate_trace_api_v1_traces_trace_id_annotations_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **trace_id** | **str**|  | 
 **agentic_annotation_request** | [**AgenticAnnotationRequest**](AgenticAnnotationRequest.md)|  | 

### Return type

[**AgenticAnnotationResponse**](AgenticAnnotationResponse.md)

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

# **compute_trace_metrics_api_v1_traces_trace_id_metrics_get**
> TraceResponse compute_trace_metrics_api_v1_traces_trace_id_metrics_get(trace_id)

Compute Missing Trace Metrics

Compute all missing metrics for trace spans on-demand. Returns full trace tree with computed metrics.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.trace_response import TraceResponse
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
    api_instance = arthur_observability_sdk._generated.TracesApi(api_client)
    trace_id = 'trace_id_example' # str | 

    try:
        # Compute Missing Trace Metrics
        api_response = api_instance.compute_trace_metrics_api_v1_traces_trace_id_metrics_get(trace_id)
        print("The response of TracesApi->compute_trace_metrics_api_v1_traces_trace_id_metrics_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TracesApi->compute_trace_metrics_api_v1_traces_trace_id_metrics_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **trace_id** | **str**|  | 

### Return type

[**TraceResponse**](TraceResponse.md)

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

# **delete_annotation_from_trace_api_v1_traces_trace_id_annotations_delete**
> delete_annotation_from_trace_api_v1_traces_trace_id_annotations_delete(trace_id)

Delete an annotation from a trace

Delete an annotation from a trace

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
    api_instance = arthur_observability_sdk._generated.TracesApi(api_client)
    trace_id = 'trace_id_example' # str | 

    try:
        # Delete an annotation from a trace
        api_instance.delete_annotation_from_trace_api_v1_traces_trace_id_annotations_delete(trace_id)
    except Exception as e:
        print("Exception when calling TracesApi->delete_annotation_from_trace_api_v1_traces_trace_id_annotations_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **trace_id** | **str**|  | 

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
**204** | Annotation deleted from trace. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_annotation_by_id_api_v1_traces_annotations_annotation_id_get**
> AgenticAnnotationResponse get_annotation_by_id_api_v1_traces_annotations_annotation_id_get(annotation_id)

Get an annotation by id

Get an annotation by id

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.agentic_annotation_response import AgenticAnnotationResponse
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
    api_instance = arthur_observability_sdk._generated.TracesApi(api_client)
    annotation_id = 'annotation_id_example' # str | 

    try:
        # Get an annotation by id
        api_response = api_instance.get_annotation_by_id_api_v1_traces_annotations_annotation_id_get(annotation_id)
        print("The response of TracesApi->get_annotation_by_id_api_v1_traces_annotations_annotation_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TracesApi->get_annotation_by_id_api_v1_traces_annotations_annotation_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **annotation_id** | **str**|  | 

### Return type

[**AgenticAnnotationResponse**](AgenticAnnotationResponse.md)

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

# **get_trace_by_id_api_v1_traces_trace_id_get**
> TraceResponse get_trace_by_id_api_v1_traces_trace_id_get(trace_id)

Get Single Trace

Get complete trace tree with existing metrics (no computation). Returns full trace structure with spans.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.trace_response import TraceResponse
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
    api_instance = arthur_observability_sdk._generated.TracesApi(api_client)
    trace_id = 'trace_id_example' # str | 

    try:
        # Get Single Trace
        api_response = api_instance.get_trace_by_id_api_v1_traces_trace_id_get(trace_id)
        print("The response of TracesApi->get_trace_by_id_api_v1_traces_trace_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TracesApi->get_trace_by_id_api_v1_traces_trace_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **trace_id** | **str**|  | 

### Return type

[**TraceResponse**](TraceResponse.md)

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

# **list_annotations_for_trace_api_v1_traces_trace_id_annotations_get**
> ListAgenticAnnotationsResponse list_annotations_for_trace_api_v1_traces_trace_id_annotations_get(trace_id, sort=sort, page_size=page_size, page=page, continuous_eval_id=continuous_eval_id, annotation_type=annotation_type, annotation_score=annotation_score, run_status=run_status, created_after=created_after, created_before=created_before)

List Annotations for a Trace

List annotations for a trace

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.continuous_eval_run_status import ContinuousEvalRunStatus
from arthur_observability_sdk._generated.models.list_agentic_annotations_response import ListAgenticAnnotationsResponse
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
    api_instance = arthur_observability_sdk._generated.TracesApi(api_client)
    trace_id = 'trace_id_example' # str | 
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)
    continuous_eval_id = 'continuous_eval_id_example' # str | ID of the continuous eval to filter on. (optional)
    annotation_type = 'annotation_type_example' # str | Annotation type to filter on. (optional)
    annotation_score = 56 # int | Annotation score to filter on. (optional)
    run_status = arthur_observability_sdk._generated.ContinuousEvalRunStatus() # ContinuousEvalRunStatus | Run status to filter on. (optional)
    created_after = 'created_after_example' # str | Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC). (optional)
    created_before = 'created_before_example' # str | Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC). (optional)

    try:
        # List Annotations for a Trace
        api_response = api_instance.list_annotations_for_trace_api_v1_traces_trace_id_annotations_get(trace_id, sort=sort, page_size=page_size, page=page, continuous_eval_id=continuous_eval_id, annotation_type=annotation_type, annotation_score=annotation_score, run_status=run_status, created_after=created_after, created_before=created_before)
        print("The response of TracesApi->list_annotations_for_trace_api_v1_traces_trace_id_annotations_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TracesApi->list_annotations_for_trace_api_v1_traces_trace_id_annotations_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **trace_id** | **str**|  | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]
 **continuous_eval_id** | **str**| ID of the continuous eval to filter on. | [optional] 
 **annotation_type** | **str**| Annotation type to filter on. | [optional] 
 **annotation_score** | **int**| Annotation score to filter on. | [optional] 
 **run_status** | [**ContinuousEvalRunStatus**](.md)| Run status to filter on. | [optional] 
 **created_after** | **str**| Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC). | [optional] 
 **created_before** | **str**| Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC). | [optional] 

### Return type

[**ListAgenticAnnotationsResponse**](ListAgenticAnnotationsResponse.md)

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

# **list_traces_metadata_api_v1_traces_get**
> TraceListResponse list_traces_metadata_api_v1_traces_get(task_ids, include_spans=include_spans, sort=sort, page_size=page_size, page=page, trace_ids=trace_ids, start_time=start_time, end_time=end_time, tool_name=tool_name, span_types=span_types, annotation_score=annotation_score, annotation_type=annotation_type, continuous_eval_run_status=continuous_eval_run_status, continuous_eval_name=continuous_eval_name, span_ids=span_ids, session_ids=session_ids, user_ids=user_ids, span_name=span_name, span_name_contains=span_name_contains, status_code=status_code, query_relevance_eq=query_relevance_eq, query_relevance_gt=query_relevance_gt, query_relevance_gte=query_relevance_gte, query_relevance_lt=query_relevance_lt, query_relevance_lte=query_relevance_lte, response_relevance_eq=response_relevance_eq, response_relevance_gt=response_relevance_gt, response_relevance_gte=response_relevance_gte, response_relevance_lt=response_relevance_lt, response_relevance_lte=response_relevance_lte, tool_selection=tool_selection, tool_usage=tool_usage, trace_duration_eq=trace_duration_eq, trace_duration_gt=trace_duration_gt, trace_duration_gte=trace_duration_gte, trace_duration_lt=trace_duration_lt, trace_duration_lte=trace_duration_lte)

List Trace Metadata

Get lightweight trace metadata for browsing/filtering operations. Returns metadata only without spans or metrics for fast performance. Set include_spans=true to include flat list of spans for each trace.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.agentic_annotation_type import AgenticAnnotationType
from arthur_observability_sdk._generated.models.continuous_eval_run_status import ContinuousEvalRunStatus
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.tool_class_enum import ToolClassEnum
from arthur_observability_sdk._generated.models.trace_list_response import TraceListResponse
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
    api_instance = arthur_observability_sdk._generated.TracesApi(api_client)
    task_ids = ['task_ids_example'] # List[str] | Task IDs to filter on. At least one is required.
    include_spans = False # bool | Include flat list of spans for each trace. Defaults to false for performance. (optional) (default to False)
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)
    trace_ids = ['trace_ids_example'] # List[str] | Trace IDs to filter on. Optional. (optional)
    start_time = '2013-10-20T19:20:30+01:00' # datetime | Inclusive start date in ISO8601 string format. Use local time (not UTC). (optional)
    end_time = '2013-10-20T19:20:30+01:00' # datetime | Exclusive end date in ISO8601 string format. Use local time (not UTC). (optional)
    tool_name = 'tool_name_example' # str | Return only results with this tool name. (optional)
    span_types = ['span_types_example'] # List[str] | Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN (optional)
    annotation_score = 56 # int | Filter by trace annotation score (0 or 1). (optional)
    annotation_type = arthur_observability_sdk._generated.AgenticAnnotationType() # AgenticAnnotationType | Filter by trace annotation type (i.e. 'human' or 'continuous_eval'). (optional)
    continuous_eval_run_status = arthur_observability_sdk._generated.ContinuousEvalRunStatus() # ContinuousEvalRunStatus | Filter by trace annotation run status (e.g. 'passed', 'failed', etc.). (optional)
    continuous_eval_name = 'continuous_eval_name_example' # str | Filter by continuous eval name. (optional)
    span_ids = ['span_ids_example'] # List[str] | Span IDs to filter on. Optional. (optional)
    session_ids = ['session_ids_example'] # List[str] | Session IDs to filter on. Optional. (optional)
    user_ids = ['user_ids_example'] # List[str] | User IDs to filter on. Optional. (optional)
    span_name = 'span_name_example' # str | Return only results with this span name. (optional)
    span_name_contains = 'span_name_contains_example' # str | Return only results where span name contains this substring. (optional)
    status_code = ['status_code_example'] # List[str] | Status codes to filter on. Optional. Valid values: Ok, Error, Unset. (optional)
    query_relevance_eq = 3.4 # float | Equal to this value. (optional)
    query_relevance_gt = 3.4 # float | Greater than this value. (optional)
    query_relevance_gte = 3.4 # float | Greater than or equal to this value. (optional)
    query_relevance_lt = 3.4 # float | Less than this value. (optional)
    query_relevance_lte = 3.4 # float | Less than or equal to this value. (optional)
    response_relevance_eq = 3.4 # float | Equal to this value. (optional)
    response_relevance_gt = 3.4 # float | Greater than this value. (optional)
    response_relevance_gte = 3.4 # float | Greater than or equal to this value. (optional)
    response_relevance_lt = 3.4 # float | Less than this value. (optional)
    response_relevance_lte = 3.4 # float | Less than or equal to this value. (optional)
    tool_selection = arthur_observability_sdk._generated.ToolClassEnum() # ToolClassEnum | Tool selection evaluation result. (optional)
    tool_usage = arthur_observability_sdk._generated.ToolClassEnum() # ToolClassEnum | Tool usage evaluation result. (optional)
    trace_duration_eq = 3.4 # float | Duration exactly equal to this value (seconds). (optional)
    trace_duration_gt = 3.4 # float | Duration greater than this value (seconds). (optional)
    trace_duration_gte = 3.4 # float | Duration greater than or equal to this value (seconds). (optional)
    trace_duration_lt = 3.4 # float | Duration less than this value (seconds). (optional)
    trace_duration_lte = 3.4 # float | Duration less than or equal to this value (seconds). (optional)

    try:
        # List Trace Metadata
        api_response = api_instance.list_traces_metadata_api_v1_traces_get(task_ids, include_spans=include_spans, sort=sort, page_size=page_size, page=page, trace_ids=trace_ids, start_time=start_time, end_time=end_time, tool_name=tool_name, span_types=span_types, annotation_score=annotation_score, annotation_type=annotation_type, continuous_eval_run_status=continuous_eval_run_status, continuous_eval_name=continuous_eval_name, span_ids=span_ids, session_ids=session_ids, user_ids=user_ids, span_name=span_name, span_name_contains=span_name_contains, status_code=status_code, query_relevance_eq=query_relevance_eq, query_relevance_gt=query_relevance_gt, query_relevance_gte=query_relevance_gte, query_relevance_lt=query_relevance_lt, query_relevance_lte=query_relevance_lte, response_relevance_eq=response_relevance_eq, response_relevance_gt=response_relevance_gt, response_relevance_gte=response_relevance_gte, response_relevance_lt=response_relevance_lt, response_relevance_lte=response_relevance_lte, tool_selection=tool_selection, tool_usage=tool_usage, trace_duration_eq=trace_duration_eq, trace_duration_gt=trace_duration_gt, trace_duration_gte=trace_duration_gte, trace_duration_lt=trace_duration_lt, trace_duration_lte=trace_duration_lte)
        print("The response of TracesApi->list_traces_metadata_api_v1_traces_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TracesApi->list_traces_metadata_api_v1_traces_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_ids** | [**List[str]**](str.md)| Task IDs to filter on. At least one is required. | 
 **include_spans** | **bool**| Include flat list of spans for each trace. Defaults to false for performance. | [optional] [default to False]
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]
 **trace_ids** | [**List[str]**](str.md)| Trace IDs to filter on. Optional. | [optional] 
 **start_time** | **datetime**| Inclusive start date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **end_time** | **datetime**| Exclusive end date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **tool_name** | **str**| Return only results with this tool name. | [optional] 
 **span_types** | [**List[str]**](str.md)| Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN | [optional] 
 **annotation_score** | **int**| Filter by trace annotation score (0 or 1). | [optional] 
 **annotation_type** | [**AgenticAnnotationType**](.md)| Filter by trace annotation type (i.e. &#39;human&#39; or &#39;continuous_eval&#39;). | [optional] 
 **continuous_eval_run_status** | [**ContinuousEvalRunStatus**](.md)| Filter by trace annotation run status (e.g. &#39;passed&#39;, &#39;failed&#39;, etc.). | [optional] 
 **continuous_eval_name** | **str**| Filter by continuous eval name. | [optional] 
 **span_ids** | [**List[str]**](str.md)| Span IDs to filter on. Optional. | [optional] 
 **session_ids** | [**List[str]**](str.md)| Session IDs to filter on. Optional. | [optional] 
 **user_ids** | [**List[str]**](str.md)| User IDs to filter on. Optional. | [optional] 
 **span_name** | **str**| Return only results with this span name. | [optional] 
 **span_name_contains** | **str**| Return only results where span name contains this substring. | [optional] 
 **status_code** | [**List[str]**](str.md)| Status codes to filter on. Optional. Valid values: Ok, Error, Unset. | [optional] 
 **query_relevance_eq** | **float**| Equal to this value. | [optional] 
 **query_relevance_gt** | **float**| Greater than this value. | [optional] 
 **query_relevance_gte** | **float**| Greater than or equal to this value. | [optional] 
 **query_relevance_lt** | **float**| Less than this value. | [optional] 
 **query_relevance_lte** | **float**| Less than or equal to this value. | [optional] 
 **response_relevance_eq** | **float**| Equal to this value. | [optional] 
 **response_relevance_gt** | **float**| Greater than this value. | [optional] 
 **response_relevance_gte** | **float**| Greater than or equal to this value. | [optional] 
 **response_relevance_lt** | **float**| Less than this value. | [optional] 
 **response_relevance_lte** | **float**| Less than or equal to this value. | [optional] 
 **tool_selection** | [**ToolClassEnum**](.md)| Tool selection evaluation result. | [optional] 
 **tool_usage** | [**ToolClassEnum**](.md)| Tool usage evaluation result. | [optional] 
 **trace_duration_eq** | **float**| Duration exactly equal to this value (seconds). | [optional] 
 **trace_duration_gt** | **float**| Duration greater than this value (seconds). | [optional] 
 **trace_duration_gte** | **float**| Duration greater than or equal to this value (seconds). | [optional] 
 **trace_duration_lt** | **float**| Duration less than this value (seconds). | [optional] 
 **trace_duration_lte** | **float**| Duration less than or equal to this value (seconds). | [optional] 

### Return type

[**TraceListResponse**](TraceListResponse.md)

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

# **receive_traces_api_v1_traces_post**
> object receive_traces_api_v1_traces_post(body)

Receive Traces

Receiver for OpenInference trace standard.

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
    api_instance = arthur_observability_sdk._generated.TracesApi(api_client)
    body = None # bytearray | 

    try:
        # Receive Traces
        api_response = api_instance.receive_traces_api_v1_traces_post(body)
        print("The response of TracesApi->receive_traces_api_v1_traces_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TracesApi->receive_traces_api_v1_traces_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | **bytearray**|  | 

### Return type

**object**

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

# **receive_traces_v1_traces_post**
> object receive_traces_v1_traces_post(body)

Receive Traces

Receiver for OpenInference trace standard.

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
    api_instance = arthur_observability_sdk._generated.TracesApi(api_client)
    body = None # bytearray | 

    try:
        # Receive Traces
        api_response = api_instance.receive_traces_v1_traces_post(body)
        print("The response of TracesApi->receive_traces_v1_traces_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TracesApi->receive_traces_v1_traces_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | **bytearray**|  | 

### Return type

**object**

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

