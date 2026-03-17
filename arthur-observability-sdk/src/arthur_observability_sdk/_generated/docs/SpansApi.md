# arthur_observability_sdk._generated.SpansApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**compute_span_metrics_api_v1_traces_spans_span_id_metrics_get**](SpansApi.md#compute_span_metrics_api_v1_traces_spans_span_id_metrics_get) | **GET** /api/v1/traces/spans/{span_id}/metrics | Compute Missing Span Metrics
[**compute_span_metrics_v1_span_span_id_metrics_get**](SpansApi.md#compute_span_metrics_v1_span_span_id_metrics_get) | **GET** /v1/span/{span_id}/metrics | Compute Metrics for Span
[**get_span_by_id_api_v1_traces_spans_span_id_get**](SpansApi.md#get_span_by_id_api_v1_traces_spans_span_id_get) | **GET** /api/v1/traces/spans/{span_id} | Get Single Span
[**get_unregistered_root_spans_api_v1_traces_spans_unregistered_get**](SpansApi.md#get_unregistered_root_spans_api_v1_traces_spans_unregistered_get) | **GET** /api/v1/traces/spans/unregistered | Get Unregistered Root Spans
[**list_spans_metadata_api_v1_traces_spans_get**](SpansApi.md#list_spans_metadata_api_v1_traces_spans_get) | **GET** /api/v1/traces/spans | List Span Metadata with Filtering
[**query_spans_by_type_v1_spans_query_get**](SpansApi.md#query_spans_by_type_v1_spans_query_get) | **GET** /v1/spans/query | Query Spans By Type
[**query_spans_v1_traces_query_get**](SpansApi.md#query_spans_v1_traces_query_get) | **GET** /v1/traces/query | Query Traces
[**query_spans_with_metrics_v1_traces_metrics_get**](SpansApi.md#query_spans_with_metrics_v1_traces_metrics_get) | **GET** /v1/traces/metrics/ | Compute Missing Metrics and Query Traces


# **compute_span_metrics_api_v1_traces_spans_span_id_metrics_get**
> SpanWithMetricsResponse compute_span_metrics_api_v1_traces_spans_span_id_metrics_get(span_id)

Compute Missing Span Metrics

Compute all missing metrics for a single span on-demand. Returns span with computed metrics.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.span_with_metrics_response import SpanWithMetricsResponse
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
    api_instance = arthur_observability_sdk._generated.SpansApi(api_client)
    span_id = 'span_id_example' # str | 

    try:
        # Compute Missing Span Metrics
        api_response = api_instance.compute_span_metrics_api_v1_traces_spans_span_id_metrics_get(span_id)
        print("The response of SpansApi->compute_span_metrics_api_v1_traces_spans_span_id_metrics_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SpansApi->compute_span_metrics_api_v1_traces_spans_span_id_metrics_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **span_id** | **str**|  | 

### Return type

[**SpanWithMetricsResponse**](SpanWithMetricsResponse.md)

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

# **compute_span_metrics_v1_span_span_id_metrics_get**
> SpanWithMetricsResponse compute_span_metrics_v1_span_span_id_metrics_get(span_id)

Compute Metrics for Span

Compute metrics for a single span. Validates that the span is an LLM span.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.span_with_metrics_response import SpanWithMetricsResponse
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
    api_instance = arthur_observability_sdk._generated.SpansApi(api_client)
    span_id = 'span_id_example' # str | 

    try:
        # Compute Metrics for Span
        api_response = api_instance.compute_span_metrics_v1_span_span_id_metrics_get(span_id)
        print("The response of SpansApi->compute_span_metrics_v1_span_span_id_metrics_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SpansApi->compute_span_metrics_v1_span_span_id_metrics_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **span_id** | **str**|  | 

### Return type

[**SpanWithMetricsResponse**](SpanWithMetricsResponse.md)

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

# **get_span_by_id_api_v1_traces_spans_span_id_get**
> SpanWithMetricsResponse get_span_by_id_api_v1_traces_spans_span_id_get(span_id)

Get Single Span

Get single span with existing metrics (no computation). Returns full span object with any existing metrics.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.span_with_metrics_response import SpanWithMetricsResponse
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
    api_instance = arthur_observability_sdk._generated.SpansApi(api_client)
    span_id = 'span_id_example' # str | 

    try:
        # Get Single Span
        api_response = api_instance.get_span_by_id_api_v1_traces_spans_span_id_get(span_id)
        print("The response of SpansApi->get_span_by_id_api_v1_traces_spans_span_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SpansApi->get_span_by_id_api_v1_traces_spans_span_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **span_id** | **str**|  | 

### Return type

[**SpanWithMetricsResponse**](SpanWithMetricsResponse.md)

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

# **get_unregistered_root_spans_api_v1_traces_spans_unregistered_get**
> UnregisteredRootSpansResponse get_unregistered_root_spans_api_v1_traces_spans_unregistered_get(start_time=start_time, end_time=end_time, sort=sort, page_size=page_size, page=page)

Get Unregistered Root Spans

Get grouped root spans for traces without task_id. Groups are ordered by count descending. Supports pagination. Time bounds (start_time/end_time) are recommended for performance on large datasets.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.unregistered_root_spans_response import UnregisteredRootSpansResponse
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
    api_instance = arthur_observability_sdk._generated.SpansApi(api_client)
    start_time = '2013-10-20T19:20:30+01:00' # datetime | Inclusive start date in ISO8601 string format. Use local time (not UTC). (optional)
    end_time = '2013-10-20T19:20:30+01:00' # datetime | Inclusive end date in ISO8601 string format. Use local time (not UTC). (optional)
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get Unregistered Root Spans
        api_response = api_instance.get_unregistered_root_spans_api_v1_traces_spans_unregistered_get(start_time=start_time, end_time=end_time, sort=sort, page_size=page_size, page=page)
        print("The response of SpansApi->get_unregistered_root_spans_api_v1_traces_spans_unregistered_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SpansApi->get_unregistered_root_spans_api_v1_traces_spans_unregistered_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **start_time** | **datetime**| Inclusive start date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **end_time** | **datetime**| Inclusive end date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**UnregisteredRootSpansResponse**](UnregisteredRootSpansResponse.md)

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

# **list_spans_metadata_api_v1_traces_spans_get**
> SpanListResponse list_spans_metadata_api_v1_traces_spans_get(task_ids, sort=sort, page_size=page_size, page=page, trace_ids=trace_ids, start_time=start_time, end_time=end_time, tool_name=tool_name, span_types=span_types, annotation_score=annotation_score, annotation_type=annotation_type, continuous_eval_run_status=continuous_eval_run_status, continuous_eval_name=continuous_eval_name, span_ids=span_ids, session_ids=session_ids, user_ids=user_ids, span_name=span_name, span_name_contains=span_name_contains, status_code=status_code, query_relevance_eq=query_relevance_eq, query_relevance_gt=query_relevance_gt, query_relevance_gte=query_relevance_gte, query_relevance_lt=query_relevance_lt, query_relevance_lte=query_relevance_lte, response_relevance_eq=response_relevance_eq, response_relevance_gt=response_relevance_gt, response_relevance_gte=response_relevance_gte, response_relevance_lt=response_relevance_lt, response_relevance_lte=response_relevance_lte, tool_selection=tool_selection, tool_usage=tool_usage, trace_duration_eq=trace_duration_eq, trace_duration_gt=trace_duration_gt, trace_duration_gte=trace_duration_gte, trace_duration_lt=trace_duration_lt, trace_duration_lte=trace_duration_lte)

List Span Metadata with Filtering

Get lightweight span metadata with comprehensive filtering support. Returns individual spans that match filtering criteria with the same filtering capabilities as trace filtering. Supports trace-level filters, span-level filters, and metric filters.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.agentic_annotation_type import AgenticAnnotationType
from arthur_observability_sdk._generated.models.continuous_eval_run_status import ContinuousEvalRunStatus
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.span_list_response import SpanListResponse
from arthur_observability_sdk._generated.models.tool_class_enum import ToolClassEnum
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
    api_instance = arthur_observability_sdk._generated.SpansApi(api_client)
    task_ids = ['task_ids_example'] # List[str] | Task IDs to filter on. At least one is required.
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
        # List Span Metadata with Filtering
        api_response = api_instance.list_spans_metadata_api_v1_traces_spans_get(task_ids, sort=sort, page_size=page_size, page=page, trace_ids=trace_ids, start_time=start_time, end_time=end_time, tool_name=tool_name, span_types=span_types, annotation_score=annotation_score, annotation_type=annotation_type, continuous_eval_run_status=continuous_eval_run_status, continuous_eval_name=continuous_eval_name, span_ids=span_ids, session_ids=session_ids, user_ids=user_ids, span_name=span_name, span_name_contains=span_name_contains, status_code=status_code, query_relevance_eq=query_relevance_eq, query_relevance_gt=query_relevance_gt, query_relevance_gte=query_relevance_gte, query_relevance_lt=query_relevance_lt, query_relevance_lte=query_relevance_lte, response_relevance_eq=response_relevance_eq, response_relevance_gt=response_relevance_gt, response_relevance_gte=response_relevance_gte, response_relevance_lt=response_relevance_lt, response_relevance_lte=response_relevance_lte, tool_selection=tool_selection, tool_usage=tool_usage, trace_duration_eq=trace_duration_eq, trace_duration_gt=trace_duration_gt, trace_duration_gte=trace_duration_gte, trace_duration_lt=trace_duration_lt, trace_duration_lte=trace_duration_lte)
        print("The response of SpansApi->list_spans_metadata_api_v1_traces_spans_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SpansApi->list_spans_metadata_api_v1_traces_spans_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_ids** | [**List[str]**](str.md)| Task IDs to filter on. At least one is required. | 
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

[**SpanListResponse**](SpanListResponse.md)

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

# **query_spans_by_type_v1_spans_query_get**
> QuerySpansResponse query_spans_by_type_v1_spans_query_get(task_ids, span_types=span_types, start_time=start_time, end_time=end_time, sort=sort, page_size=page_size, page=page)

Query Spans By Type

Query spans filtered by span type. Task IDs are required. Returns spans with any existing metrics but does not compute new ones.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.query_spans_response import QuerySpansResponse
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
    api_instance = arthur_observability_sdk._generated.SpansApi(api_client)
    task_ids = ['task_ids_example'] # List[str] | Task IDs to filter on. At least one is required.
    span_types = ['span_types_example'] # List[str] | Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN (optional)
    start_time = '2013-10-20T19:20:30+01:00' # datetime | Inclusive start date in ISO8601 string format. Use local time (not UTC). (optional)
    end_time = '2013-10-20T19:20:30+01:00' # datetime | Exclusive end date in ISO8601 string format. Use local time (not UTC). (optional)
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Query Spans By Type
        api_response = api_instance.query_spans_by_type_v1_spans_query_get(task_ids, span_types=span_types, start_time=start_time, end_time=end_time, sort=sort, page_size=page_size, page=page)
        print("The response of SpansApi->query_spans_by_type_v1_spans_query_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SpansApi->query_spans_by_type_v1_spans_query_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_ids** | [**List[str]**](str.md)| Task IDs to filter on. At least one is required. | 
 **span_types** | [**List[str]**](str.md)| Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN | [optional] 
 **start_time** | **datetime**| Inclusive start date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **end_time** | **datetime**| Exclusive end date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**QuerySpansResponse**](QuerySpansResponse.md)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**400** | Invalid span types, parameters, or validation error |  -  |
**404** | No spans found |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **query_spans_v1_traces_query_get**
> QueryTracesWithMetricsResponse query_spans_v1_traces_query_get(task_ids, sort=sort, page_size=page_size, page=page, trace_ids=trace_ids, start_time=start_time, end_time=end_time, tool_name=tool_name, span_types=span_types, annotation_score=annotation_score, annotation_type=annotation_type, continuous_eval_run_status=continuous_eval_run_status, continuous_eval_name=continuous_eval_name, span_ids=span_ids, session_ids=session_ids, user_ids=user_ids, span_name=span_name, span_name_contains=span_name_contains, status_code=status_code, query_relevance_eq=query_relevance_eq, query_relevance_gt=query_relevance_gt, query_relevance_gte=query_relevance_gte, query_relevance_lt=query_relevance_lt, query_relevance_lte=query_relevance_lte, response_relevance_eq=response_relevance_eq, response_relevance_gt=response_relevance_gt, response_relevance_gte=response_relevance_gte, response_relevance_lt=response_relevance_lt, response_relevance_lte=response_relevance_lte, tool_selection=tool_selection, tool_usage=tool_usage, trace_duration_eq=trace_duration_eq, trace_duration_gt=trace_duration_gt, trace_duration_gte=trace_duration_gte, trace_duration_lt=trace_duration_lt, trace_duration_lte=trace_duration_lte)

Query Traces

Query traces with comprehensive filtering. Returns traces containing spans that match the filters, not just the spans themselves.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.agentic_annotation_type import AgenticAnnotationType
from arthur_observability_sdk._generated.models.continuous_eval_run_status import ContinuousEvalRunStatus
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.query_traces_with_metrics_response import QueryTracesWithMetricsResponse
from arthur_observability_sdk._generated.models.tool_class_enum import ToolClassEnum
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
    api_instance = arthur_observability_sdk._generated.SpansApi(api_client)
    task_ids = ['task_ids_example'] # List[Optional[str]] | Task IDs to filter on. At least one is required.
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)
    trace_ids = ['trace_ids_example'] # List[Optional[str]] | Trace IDs to filter on. Optional. (optional)
    start_time = '2013-10-20T19:20:30+01:00' # datetime | Inclusive start date in ISO8601 string format. Use local time (not UTC). (optional)
    end_time = '2013-10-20T19:20:30+01:00' # datetime | Exclusive end date in ISO8601 string format. Use local time (not UTC). (optional)
    tool_name = 'tool_name_example' # str | Return only results with this tool name. (optional)
    span_types = ['span_types_example'] # List[Optional[str]] | Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN (optional)
    annotation_score = 56 # int | Filter by trace annotation score (0 or 1). (optional)
    annotation_type = arthur_observability_sdk._generated.AgenticAnnotationType() # AgenticAnnotationType | Filter by trace annotation type (i.e. 'human' or 'continuous_eval'). (optional)
    continuous_eval_run_status = arthur_observability_sdk._generated.ContinuousEvalRunStatus() # ContinuousEvalRunStatus | Filter by trace annotation run status (e.g. 'passed', 'failed', etc.). (optional)
    continuous_eval_name = 'continuous_eval_name_example' # str | Filter by continuous eval name. (optional)
    span_ids = ['span_ids_example'] # List[Optional[str]] | Span IDs to filter on. Optional. (optional)
    session_ids = ['session_ids_example'] # List[Optional[str]] | Session IDs to filter on. Optional. (optional)
    user_ids = ['user_ids_example'] # List[Optional[str]] | User IDs to filter on. Optional. (optional)
    span_name = 'span_name_example' # str | Return only results with this span name. (optional)
    span_name_contains = 'span_name_contains_example' # str | Return only results where span name contains this substring. (optional)
    status_code = ['status_code_example'] # List[Optional[str]] | Status codes to filter on. Optional. Valid values: Ok, Error, Unset. (optional)
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
        # Query Traces
        api_response = api_instance.query_spans_v1_traces_query_get(task_ids, sort=sort, page_size=page_size, page=page, trace_ids=trace_ids, start_time=start_time, end_time=end_time, tool_name=tool_name, span_types=span_types, annotation_score=annotation_score, annotation_type=annotation_type, continuous_eval_run_status=continuous_eval_run_status, continuous_eval_name=continuous_eval_name, span_ids=span_ids, session_ids=session_ids, user_ids=user_ids, span_name=span_name, span_name_contains=span_name_contains, status_code=status_code, query_relevance_eq=query_relevance_eq, query_relevance_gt=query_relevance_gt, query_relevance_gte=query_relevance_gte, query_relevance_lt=query_relevance_lt, query_relevance_lte=query_relevance_lte, response_relevance_eq=response_relevance_eq, response_relevance_gt=response_relevance_gt, response_relevance_gte=response_relevance_gte, response_relevance_lt=response_relevance_lt, response_relevance_lte=response_relevance_lte, tool_selection=tool_selection, tool_usage=tool_usage, trace_duration_eq=trace_duration_eq, trace_duration_gt=trace_duration_gt, trace_duration_gte=trace_duration_gte, trace_duration_lt=trace_duration_lt, trace_duration_lte=trace_duration_lte)
        print("The response of SpansApi->query_spans_v1_traces_query_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SpansApi->query_spans_v1_traces_query_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_ids** | [**List[Optional[str]]**](str.md)| Task IDs to filter on. At least one is required. | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]
 **trace_ids** | [**List[Optional[str]]**](str.md)| Trace IDs to filter on. Optional. | [optional] 
 **start_time** | **datetime**| Inclusive start date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **end_time** | **datetime**| Exclusive end date in ISO8601 string format. Use local time (not UTC). | [optional] 
 **tool_name** | **str**| Return only results with this tool name. | [optional] 
 **span_types** | [**List[Optional[str]]**](str.md)| Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN | [optional] 
 **annotation_score** | **int**| Filter by trace annotation score (0 or 1). | [optional] 
 **annotation_type** | [**AgenticAnnotationType**](.md)| Filter by trace annotation type (i.e. &#39;human&#39; or &#39;continuous_eval&#39;). | [optional] 
 **continuous_eval_run_status** | [**ContinuousEvalRunStatus**](.md)| Filter by trace annotation run status (e.g. &#39;passed&#39;, &#39;failed&#39;, etc.). | [optional] 
 **continuous_eval_name** | **str**| Filter by continuous eval name. | [optional] 
 **span_ids** | [**List[Optional[str]]**](str.md)| Span IDs to filter on. Optional. | [optional] 
 **session_ids** | [**List[Optional[str]]**](str.md)| Session IDs to filter on. Optional. | [optional] 
 **user_ids** | [**List[Optional[str]]**](str.md)| User IDs to filter on. Optional. | [optional] 
 **span_name** | **str**| Return only results with this span name. | [optional] 
 **span_name_contains** | **str**| Return only results where span name contains this substring. | [optional] 
 **status_code** | [**List[Optional[str]]**](str.md)| Status codes to filter on. Optional. Valid values: Ok, Error, Unset. | [optional] 
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

[**QueryTracesWithMetricsResponse**](QueryTracesWithMetricsResponse.md)

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

# **query_spans_with_metrics_v1_traces_metrics_get**
> QueryTracesWithMetricsResponse query_spans_with_metrics_v1_traces_metrics_get(task_ids, sort=sort, page_size=page_size, page=page, trace_ids=trace_ids, start_time=start_time, end_time=end_time, tool_name=tool_name, span_types=span_types, annotation_score=annotation_score, annotation_type=annotation_type, continuous_eval_run_status=continuous_eval_run_status, continuous_eval_name=continuous_eval_name, span_ids=span_ids, session_ids=session_ids, user_ids=user_ids, span_name=span_name, span_name_contains=span_name_contains, status_code=status_code, query_relevance_eq=query_relevance_eq, query_relevance_gt=query_relevance_gt, query_relevance_gte=query_relevance_gte, query_relevance_lt=query_relevance_lt, query_relevance_lte=query_relevance_lte, response_relevance_eq=response_relevance_eq, response_relevance_gt=response_relevance_gt, response_relevance_gte=response_relevance_gte, response_relevance_lt=response_relevance_lt, response_relevance_lte=response_relevance_lte, tool_selection=tool_selection, tool_usage=tool_usage, trace_duration_eq=trace_duration_eq, trace_duration_gt=trace_duration_gt, trace_duration_gte=trace_duration_gte, trace_duration_lt=trace_duration_lt, trace_duration_lte=trace_duration_lte)

Compute Missing Metrics and Query Traces

Query traces with comprehensive filtering and compute metrics. Returns traces containing spans that match the filters with computed metrics.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.agentic_annotation_type import AgenticAnnotationType
from arthur_observability_sdk._generated.models.continuous_eval_run_status import ContinuousEvalRunStatus
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.query_traces_with_metrics_response import QueryTracesWithMetricsResponse
from arthur_observability_sdk._generated.models.tool_class_enum import ToolClassEnum
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
    api_instance = arthur_observability_sdk._generated.SpansApi(api_client)
    task_ids = ['task_ids_example'] # List[str] | Task IDs to filter on. At least one is required.
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
        # Compute Missing Metrics and Query Traces
        api_response = api_instance.query_spans_with_metrics_v1_traces_metrics_get(task_ids, sort=sort, page_size=page_size, page=page, trace_ids=trace_ids, start_time=start_time, end_time=end_time, tool_name=tool_name, span_types=span_types, annotation_score=annotation_score, annotation_type=annotation_type, continuous_eval_run_status=continuous_eval_run_status, continuous_eval_name=continuous_eval_name, span_ids=span_ids, session_ids=session_ids, user_ids=user_ids, span_name=span_name, span_name_contains=span_name_contains, status_code=status_code, query_relevance_eq=query_relevance_eq, query_relevance_gt=query_relevance_gt, query_relevance_gte=query_relevance_gte, query_relevance_lt=query_relevance_lt, query_relevance_lte=query_relevance_lte, response_relevance_eq=response_relevance_eq, response_relevance_gt=response_relevance_gt, response_relevance_gte=response_relevance_gte, response_relevance_lt=response_relevance_lt, response_relevance_lte=response_relevance_lte, tool_selection=tool_selection, tool_usage=tool_usage, trace_duration_eq=trace_duration_eq, trace_duration_gt=trace_duration_gt, trace_duration_gte=trace_duration_gte, trace_duration_lt=trace_duration_lt, trace_duration_lte=trace_duration_lte)
        print("The response of SpansApi->query_spans_with_metrics_v1_traces_metrics_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SpansApi->query_spans_with_metrics_v1_traces_metrics_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_ids** | [**List[str]**](str.md)| Task IDs to filter on. At least one is required. | 
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

[**QueryTracesWithMetricsResponse**](QueryTracesWithMetricsResponse.md)

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

