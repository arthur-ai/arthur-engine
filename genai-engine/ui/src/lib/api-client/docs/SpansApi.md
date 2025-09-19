# SpansApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**computeSpanMetricsV1SpanSpanIdMetricsGet**](#computespanmetricsv1spanspanidmetricsget) | **GET** /v1/span/{span_id}/metrics | Compute Metrics for Span|
|[**querySpansByTypeV1SpansQueryGet**](#queryspansbytypev1spansqueryget) | **GET** /v1/spans/query | Query Spans By Type|
|[**querySpansV1TracesQueryGet**](#queryspansv1tracesqueryget) | **GET** /v1/traces/query | Query Traces|
|[**querySpansWithMetricsV1TracesMetricsGet**](#queryspanswithmetricsv1tracesmetricsget) | **GET** /v1/traces/metrics/ | Compute Missing Metrics and Query Traces|

# **computeSpanMetricsV1SpanSpanIdMetricsGet**
> SpanWithMetricsResponse computeSpanMetricsV1SpanSpanIdMetricsGet()

Compute metrics for a single span. Validates that the span is an LLM span.

### Example

```typescript
import {
    SpansApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new SpansApi(configuration);

let spanId: string; // (default to undefined)

const { status, data } = await apiInstance.computeSpanMetricsV1SpanSpanIdMetricsGet(
    spanId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **spanId** | [**string**] |  | defaults to undefined|


### Return type

**SpanWithMetricsResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **querySpansByTypeV1SpansQueryGet**
> QuerySpansResponse querySpansByTypeV1SpansQueryGet()

Query spans filtered by span type. Task IDs are required. Returns spans with any existing metrics but does not compute new ones.

### Example

```typescript
import {
    SpansApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new SpansApi(configuration);

let taskIds: Array<string>; //Task IDs to filter on. At least one is required. (default to undefined)
let spanTypes: Array<string>; //Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN (optional) (default to undefined)
let startTime: string; //Inclusive start date in ISO8601 string format. Use local time (not UTC). (optional) (default to undefined)
let endTime: string; //Exclusive end date in ISO8601 string format. Use local time (not UTC). (optional) (default to undefined)
let sort: PaginationSortMethod; //Sort the results (asc/desc) (optional) (default to undefined)
let pageSize: number; //Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
let page: number; //Page number (optional) (default to 0)

const { status, data } = await apiInstance.querySpansByTypeV1SpansQueryGet(
    taskIds,
    spanTypes,
    startTime,
    endTime,
    sort,
    pageSize,
    page
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **taskIds** | **Array&lt;string&gt;** | Task IDs to filter on. At least one is required. | defaults to undefined|
| **spanTypes** | **Array&lt;string&gt;** | Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN | (optional) defaults to undefined|
| **startTime** | [**string**] | Inclusive start date in ISO8601 string format. Use local time (not UTC). | (optional) defaults to undefined|
| **endTime** | [**string**] | Exclusive end date in ISO8601 string format. Use local time (not UTC). | (optional) defaults to undefined|
| **sort** | **PaginationSortMethod** | Sort the results (asc/desc) | (optional) defaults to undefined|
| **pageSize** | [**number**] | Page size. Default is 10. Must be greater than 0 and less than 5000. | (optional) defaults to 10|
| **page** | [**number**] | Page number | (optional) defaults to 0|


### Return type

**QuerySpansResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**400** | Invalid span types, parameters, or validation error |  -  |
|**404** | No spans found |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **querySpansV1TracesQueryGet**
> QueryTracesWithMetricsResponse querySpansV1TracesQueryGet()

Query traces with comprehensive filtering. Returns traces containing spans that match the filters, not just the spans themselves.

### Example

```typescript
import {
    SpansApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new SpansApi(configuration);

let taskIds: Array<string>; //Task IDs to filter on. At least one is required. (default to undefined)
let sort: PaginationSortMethod; //Sort the results (asc/desc) (optional) (default to undefined)
let pageSize: number; //Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
let page: number; //Page number (optional) (default to 0)
let traceIds: Array<string>; //Trace IDs to filter on. Optional. (optional) (default to undefined)
let startTime: string; //Inclusive start date in ISO8601 string format. Use local time (not UTC). (optional) (default to undefined)
let endTime: string; //Exclusive end date in ISO8601 string format. Use local time (not UTC). (optional) (default to undefined)
let toolName: string; //Return only results with this tool name. (optional) (default to undefined)
let spanTypes: Array<string>; //Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN (optional) (default to undefined)
let queryRelevanceEq: number; //Equal to this value. (optional) (default to undefined)
let queryRelevanceGt: number; //Greater than this value. (optional) (default to undefined)
let queryRelevanceGte: number; //Greater than or equal to this value. (optional) (default to undefined)
let queryRelevanceLt: number; //Less than this value. (optional) (default to undefined)
let queryRelevanceLte: number; //Less than or equal to this value. (optional) (default to undefined)
let responseRelevanceEq: number; //Equal to this value. (optional) (default to undefined)
let responseRelevanceGt: number; //Greater than this value. (optional) (default to undefined)
let responseRelevanceGte: number; //Greater than or equal to this value. (optional) (default to undefined)
let responseRelevanceLt: number; //Less than this value. (optional) (default to undefined)
let responseRelevanceLte: number; //Less than or equal to this value. (optional) (default to undefined)
let toolSelection: ToolClassEnum; //Tool selection evaluation result. (optional) (default to undefined)
let toolUsage: ToolClassEnum; //Tool usage evaluation result. (optional) (default to undefined)
let traceDurationEq: number; //Duration exactly equal to this value (seconds). (optional) (default to undefined)
let traceDurationGt: number; //Duration greater than this value (seconds). (optional) (default to undefined)
let traceDurationGte: number; //Duration greater than or equal to this value (seconds). (optional) (default to undefined)
let traceDurationLt: number; //Duration less than this value (seconds). (optional) (default to undefined)
let traceDurationLte: number; //Duration less than or equal to this value (seconds). (optional) (default to undefined)

const { status, data } = await apiInstance.querySpansV1TracesQueryGet(
    taskIds,
    sort,
    pageSize,
    page,
    traceIds,
    startTime,
    endTime,
    toolName,
    spanTypes,
    queryRelevanceEq,
    queryRelevanceGt,
    queryRelevanceGte,
    queryRelevanceLt,
    queryRelevanceLte,
    responseRelevanceEq,
    responseRelevanceGt,
    responseRelevanceGte,
    responseRelevanceLt,
    responseRelevanceLte,
    toolSelection,
    toolUsage,
    traceDurationEq,
    traceDurationGt,
    traceDurationGte,
    traceDurationLt,
    traceDurationLte
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **taskIds** | **Array&lt;string&gt;** | Task IDs to filter on. At least one is required. | defaults to undefined|
| **sort** | **PaginationSortMethod** | Sort the results (asc/desc) | (optional) defaults to undefined|
| **pageSize** | [**number**] | Page size. Default is 10. Must be greater than 0 and less than 5000. | (optional) defaults to 10|
| **page** | [**number**] | Page number | (optional) defaults to 0|
| **traceIds** | **Array&lt;string&gt;** | Trace IDs to filter on. Optional. | (optional) defaults to undefined|
| **startTime** | [**string**] | Inclusive start date in ISO8601 string format. Use local time (not UTC). | (optional) defaults to undefined|
| **endTime** | [**string**] | Exclusive end date in ISO8601 string format. Use local time (not UTC). | (optional) defaults to undefined|
| **toolName** | [**string**] | Return only results with this tool name. | (optional) defaults to undefined|
| **spanTypes** | **Array&lt;string&gt;** | Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN | (optional) defaults to undefined|
| **queryRelevanceEq** | [**number**] | Equal to this value. | (optional) defaults to undefined|
| **queryRelevanceGt** | [**number**] | Greater than this value. | (optional) defaults to undefined|
| **queryRelevanceGte** | [**number**] | Greater than or equal to this value. | (optional) defaults to undefined|
| **queryRelevanceLt** | [**number**] | Less than this value. | (optional) defaults to undefined|
| **queryRelevanceLte** | [**number**] | Less than or equal to this value. | (optional) defaults to undefined|
| **responseRelevanceEq** | [**number**] | Equal to this value. | (optional) defaults to undefined|
| **responseRelevanceGt** | [**number**] | Greater than this value. | (optional) defaults to undefined|
| **responseRelevanceGte** | [**number**] | Greater than or equal to this value. | (optional) defaults to undefined|
| **responseRelevanceLt** | [**number**] | Less than this value. | (optional) defaults to undefined|
| **responseRelevanceLte** | [**number**] | Less than or equal to this value. | (optional) defaults to undefined|
| **toolSelection** | **ToolClassEnum** | Tool selection evaluation result. | (optional) defaults to undefined|
| **toolUsage** | **ToolClassEnum** | Tool usage evaluation result. | (optional) defaults to undefined|
| **traceDurationEq** | [**number**] | Duration exactly equal to this value (seconds). | (optional) defaults to undefined|
| **traceDurationGt** | [**number**] | Duration greater than this value (seconds). | (optional) defaults to undefined|
| **traceDurationGte** | [**number**] | Duration greater than or equal to this value (seconds). | (optional) defaults to undefined|
| **traceDurationLt** | [**number**] | Duration less than this value (seconds). | (optional) defaults to undefined|
| **traceDurationLte** | [**number**] | Duration less than or equal to this value (seconds). | (optional) defaults to undefined|


### Return type

**QueryTracesWithMetricsResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **querySpansWithMetricsV1TracesMetricsGet**
> QueryTracesWithMetricsResponse querySpansWithMetricsV1TracesMetricsGet()

Query traces with comprehensive filtering and compute metrics. Returns traces containing spans that match the filters with computed metrics.

### Example

```typescript
import {
    SpansApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new SpansApi(configuration);

let taskIds: Array<string>; //Task IDs to filter on. At least one is required. (default to undefined)
let sort: PaginationSortMethod; //Sort the results (asc/desc) (optional) (default to undefined)
let pageSize: number; //Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
let page: number; //Page number (optional) (default to 0)
let traceIds: Array<string>; //Trace IDs to filter on. Optional. (optional) (default to undefined)
let startTime: string; //Inclusive start date in ISO8601 string format. Use local time (not UTC). (optional) (default to undefined)
let endTime: string; //Exclusive end date in ISO8601 string format. Use local time (not UTC). (optional) (default to undefined)
let toolName: string; //Return only results with this tool name. (optional) (default to undefined)
let spanTypes: Array<string>; //Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN (optional) (default to undefined)
let queryRelevanceEq: number; //Equal to this value. (optional) (default to undefined)
let queryRelevanceGt: number; //Greater than this value. (optional) (default to undefined)
let queryRelevanceGte: number; //Greater than or equal to this value. (optional) (default to undefined)
let queryRelevanceLt: number; //Less than this value. (optional) (default to undefined)
let queryRelevanceLte: number; //Less than or equal to this value. (optional) (default to undefined)
let responseRelevanceEq: number; //Equal to this value. (optional) (default to undefined)
let responseRelevanceGt: number; //Greater than this value. (optional) (default to undefined)
let responseRelevanceGte: number; //Greater than or equal to this value. (optional) (default to undefined)
let responseRelevanceLt: number; //Less than this value. (optional) (default to undefined)
let responseRelevanceLte: number; //Less than or equal to this value. (optional) (default to undefined)
let toolSelection: ToolClassEnum; //Tool selection evaluation result. (optional) (default to undefined)
let toolUsage: ToolClassEnum; //Tool usage evaluation result. (optional) (default to undefined)
let traceDurationEq: number; //Duration exactly equal to this value (seconds). (optional) (default to undefined)
let traceDurationGt: number; //Duration greater than this value (seconds). (optional) (default to undefined)
let traceDurationGte: number; //Duration greater than or equal to this value (seconds). (optional) (default to undefined)
let traceDurationLt: number; //Duration less than this value (seconds). (optional) (default to undefined)
let traceDurationLte: number; //Duration less than or equal to this value (seconds). (optional) (default to undefined)

const { status, data } = await apiInstance.querySpansWithMetricsV1TracesMetricsGet(
    taskIds,
    sort,
    pageSize,
    page,
    traceIds,
    startTime,
    endTime,
    toolName,
    spanTypes,
    queryRelevanceEq,
    queryRelevanceGt,
    queryRelevanceGte,
    queryRelevanceLt,
    queryRelevanceLte,
    responseRelevanceEq,
    responseRelevanceGt,
    responseRelevanceGte,
    responseRelevanceLt,
    responseRelevanceLte,
    toolSelection,
    toolUsage,
    traceDurationEq,
    traceDurationGt,
    traceDurationGte,
    traceDurationLt,
    traceDurationLte
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **taskIds** | **Array&lt;string&gt;** | Task IDs to filter on. At least one is required. | defaults to undefined|
| **sort** | **PaginationSortMethod** | Sort the results (asc/desc) | (optional) defaults to undefined|
| **pageSize** | [**number**] | Page size. Default is 10. Must be greater than 0 and less than 5000. | (optional) defaults to 10|
| **page** | [**number**] | Page number | (optional) defaults to 0|
| **traceIds** | **Array&lt;string&gt;** | Trace IDs to filter on. Optional. | (optional) defaults to undefined|
| **startTime** | [**string**] | Inclusive start date in ISO8601 string format. Use local time (not UTC). | (optional) defaults to undefined|
| **endTime** | [**string**] | Exclusive end date in ISO8601 string format. Use local time (not UTC). | (optional) defaults to undefined|
| **toolName** | [**string**] | Return only results with this tool name. | (optional) defaults to undefined|
| **spanTypes** | **Array&lt;string&gt;** | Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN | (optional) defaults to undefined|
| **queryRelevanceEq** | [**number**] | Equal to this value. | (optional) defaults to undefined|
| **queryRelevanceGt** | [**number**] | Greater than this value. | (optional) defaults to undefined|
| **queryRelevanceGte** | [**number**] | Greater than or equal to this value. | (optional) defaults to undefined|
| **queryRelevanceLt** | [**number**] | Less than this value. | (optional) defaults to undefined|
| **queryRelevanceLte** | [**number**] | Less than or equal to this value. | (optional) defaults to undefined|
| **responseRelevanceEq** | [**number**] | Equal to this value. | (optional) defaults to undefined|
| **responseRelevanceGt** | [**number**] | Greater than this value. | (optional) defaults to undefined|
| **responseRelevanceGte** | [**number**] | Greater than or equal to this value. | (optional) defaults to undefined|
| **responseRelevanceLt** | [**number**] | Less than this value. | (optional) defaults to undefined|
| **responseRelevanceLte** | [**number**] | Less than or equal to this value. | (optional) defaults to undefined|
| **toolSelection** | **ToolClassEnum** | Tool selection evaluation result. | (optional) defaults to undefined|
| **toolUsage** | **ToolClassEnum** | Tool usage evaluation result. | (optional) defaults to undefined|
| **traceDurationEq** | [**number**] | Duration exactly equal to this value (seconds). | (optional) defaults to undefined|
| **traceDurationGt** | [**number**] | Duration greater than this value (seconds). | (optional) defaults to undefined|
| **traceDurationGte** | [**number**] | Duration greater than or equal to this value (seconds). | (optional) defaults to undefined|
| **traceDurationLt** | [**number**] | Duration less than this value (seconds). | (optional) defaults to undefined|
| **traceDurationLte** | [**number**] | Duration less than or equal to this value (seconds). | (optional) defaults to undefined|


### Return type

**QueryTracesWithMetricsResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

