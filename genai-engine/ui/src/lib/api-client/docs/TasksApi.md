# TasksApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**archiveTaskApiV2TasksTaskIdDelete**](#archivetaskapiv2taskstaskiddelete) | **DELETE** /api/v2/tasks/{task_id} | Archive Task|
|[**archiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDelete**](#archivetaskmetricapiv2taskstaskidmetricsmetriciddelete) | **DELETE** /api/v2/tasks/{task_id}/metrics/{metric_id} | Archive Task Metric|
|[**archiveTaskRuleApiV2TasksTaskIdRulesRuleIdDelete**](#archivetaskruleapiv2taskstaskidrulesruleiddelete) | **DELETE** /api/v2/tasks/{task_id}/rules/{rule_id} | Archive Task Rule|
|[**createTaskApiV2TasksPost**](#createtaskapiv2taskspost) | **POST** /api/v2/tasks | Create Task|
|[**createTaskMetricApiV2TasksTaskIdMetricsPost**](#createtaskmetricapiv2taskstaskidmetricspost) | **POST** /api/v2/tasks/{task_id}/metrics | Create Task Metric|
|[**createTaskRuleApiV2TasksTaskIdRulesPost**](#createtaskruleapiv2taskstaskidrulespost) | **POST** /api/v2/tasks/{task_id}/rules | Create Task Rule|
|[**getAllTasksApiV2TasksGet**](#getalltasksapiv2tasksget) | **GET** /api/v2/tasks | Get All Tasks|
|[**getTaskApiV2TasksTaskIdGet**](#gettaskapiv2taskstaskidget) | **GET** /api/v2/tasks/{task_id} | Get Task|
|[**redirectToTasksApiV2TaskPost**](#redirecttotasksapiv2taskpost) | **POST** /api/v2/task | Redirect To Tasks|
|[**searchTasksApiV2TasksSearchPost**](#searchtasksapiv2taskssearchpost) | **POST** /api/v2/tasks/search | Search Tasks|
|[**updateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatch**](#updatetaskmetricapiv2taskstaskidmetricsmetricidpatch) | **PATCH** /api/v2/tasks/{task_id}/metrics/{metric_id} | Update Task Metric|
|[**updateTaskRulesApiV2TasksTaskIdRulesRuleIdPatch**](#updatetaskrulesapiv2taskstaskidrulesruleidpatch) | **PATCH** /api/v2/tasks/{task_id}/rules/{rule_id} | Update Task Rules|

# **archiveTaskApiV2TasksTaskIdDelete**
> any archiveTaskApiV2TasksTaskIdDelete()

Archive task. Also archives all task-scoped rules. Associated default rules are unaffected.

### Example

```typescript
import {
    TasksApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

let taskId: string; // (default to undefined)

const { status, data } = await apiInstance.archiveTaskApiV2TasksTaskIdDelete(
    taskId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **taskId** | [**string**] |  | defaults to undefined|


### Return type

**any**

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

# **archiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDelete**
> any archiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDelete()

Archive a task metric.

### Example

```typescript
import {
    TasksApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

let taskId: string; // (default to undefined)
let metricId: string; // (default to undefined)

const { status, data } = await apiInstance.archiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDelete(
    taskId,
    metricId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **taskId** | [**string**] |  | defaults to undefined|
| **metricId** | [**string**] |  | defaults to undefined|


### Return type

**any**

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

# **archiveTaskRuleApiV2TasksTaskIdRulesRuleIdDelete**
> any archiveTaskRuleApiV2TasksTaskIdRulesRuleIdDelete()

Archive an existing rule for this task.

### Example

```typescript
import {
    TasksApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

let taskId: string; // (default to undefined)
let ruleId: string; // (default to undefined)

const { status, data } = await apiInstance.archiveTaskRuleApiV2TasksTaskIdRulesRuleIdDelete(
    taskId,
    ruleId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **taskId** | [**string**] |  | defaults to undefined|
| **ruleId** | [**string**] |  | defaults to undefined|


### Return type

**any**

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

# **createTaskApiV2TasksPost**
> TaskResponse createTaskApiV2TasksPost(newTaskRequest)

Register a new task. When a new task is created, all existing default rules will be auto-applied for this new task. Optionally specify if the task is agentic.

### Example

```typescript
import {
    TasksApi,
    Configuration,
    NewTaskRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

let newTaskRequest: NewTaskRequest; //

const { status, data } = await apiInstance.createTaskApiV2TasksPost(
    newTaskRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **newTaskRequest** | **NewTaskRequest**|  | |


### Return type

**TaskResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **createTaskMetricApiV2TasksTaskIdMetricsPost**
> any createTaskMetricApiV2TasksTaskIdMetricsPost()

Create metrics for a task. Only agentic tasks can have metrics.

### Example

```typescript
import {
    TasksApi,
    Configuration,
    NewMetricRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

let taskId: string; // (default to undefined)
let newMetricRequest: NewMetricRequest; // (optional)

const { status, data } = await apiInstance.createTaskMetricApiV2TasksTaskIdMetricsPost(
    taskId,
    newMetricRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **newMetricRequest** | **NewMetricRequest**|  | |
| **taskId** | [**string**] |  | defaults to undefined|


### Return type

**any**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **createTaskRuleApiV2TasksTaskIdRulesPost**
> RuleResponse createTaskRuleApiV2TasksTaskIdRulesPost()

Create a rule to be applied only to this task. Available rule types are KeywordRule, ModelHallucinationRuleV2, ModelSensitiveDataRule, PIIDataRule, PromptInjectionRule, RegexRule, ToxicityRule.Note: The rules are cached by the validation endpoints for 60 seconds.

### Example

```typescript
import {
    TasksApi,
    Configuration,
    NewRuleRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

let taskId: string; // (default to undefined)
let newRuleRequest: NewRuleRequest; // (optional)

const { status, data } = await apiInstance.createTaskRuleApiV2TasksTaskIdRulesPost(
    taskId,
    newRuleRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **newRuleRequest** | **NewRuleRequest**|  | |
| **taskId** | [**string**] |  | defaults to undefined|


### Return type

**RuleResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getAllTasksApiV2TasksGet**
> Array<TaskResponse> getAllTasksApiV2TasksGet()

[Deprecated] Use /tasks/search endpoint. This endpoint will be removed in a future release.

### Example

```typescript
import {
    TasksApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

const { status, data } = await apiInstance.getAllTasksApiV2TasksGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**Array<TaskResponse>**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getTaskApiV2TasksTaskIdGet**
> TaskResponse getTaskApiV2TasksTaskIdGet()

Get tasks.

### Example

```typescript
import {
    TasksApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

let taskId: string; // (default to undefined)

const { status, data } = await apiInstance.getTaskApiV2TasksTaskIdGet(
    taskId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **taskId** | [**string**] |  | defaults to undefined|


### Return type

**TaskResponse**

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

# **redirectToTasksApiV2TaskPost**
> any redirectToTasksApiV2TaskPost()

Redirect to /tasks endpoint.

### Example

```typescript
import {
    TasksApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

const { status, data } = await apiInstance.redirectToTasksApiV2TaskPost();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **searchTasksApiV2TasksSearchPost**
> SearchTasksResponse searchTasksApiV2TasksSearchPost(searchTasksRequest)

Search tasks. Can filter by task IDs, task name substring, and agentic status.

### Example

```typescript
import {
    TasksApi,
    Configuration,
    SearchTasksRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

let searchTasksRequest: SearchTasksRequest; //
let sort: PaginationSortMethod; //Sort the results (asc/desc) (optional) (default to undefined)
let pageSize: number; //Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
let page: number; //Page number (optional) (default to 0)

const { status, data } = await apiInstance.searchTasksApiV2TasksSearchPost(
    searchTasksRequest,
    sort,
    pageSize,
    page
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **searchTasksRequest** | **SearchTasksRequest**|  | |
| **sort** | **PaginationSortMethod** | Sort the results (asc/desc) | (optional) defaults to undefined|
| **pageSize** | [**number**] | Page size. Default is 10. Must be greater than 0 and less than 5000. | (optional) defaults to 10|
| **page** | [**number**] | Page number | (optional) defaults to 0|


### Return type

**SearchTasksResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **updateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatch**
> any updateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatch(updateMetricRequest, )

Update a task metric.

### Example

```typescript
import {
    TasksApi,
    Configuration,
    UpdateMetricRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

let updateMetricRequest: UpdateMetricRequest; //
let taskId: string; // (default to undefined)
let metricId: string; // (default to undefined)

const { status, data } = await apiInstance.updateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatch(
    updateMetricRequest,
    taskId,
    metricId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **updateMetricRequest** | **UpdateMetricRequest**|  | |
| **taskId** | [**string**] |  | defaults to undefined|
| **metricId** | [**string**] |  | defaults to undefined|


### Return type

**any**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **updateTaskRulesApiV2TasksTaskIdRulesRuleIdPatch**
> TaskResponse updateTaskRulesApiV2TasksTaskIdRulesRuleIdPatch(updateRuleRequest, )

Enable or disable an existing rule for this task including the default rules.

### Example

```typescript
import {
    TasksApi,
    Configuration,
    UpdateRuleRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TasksApi(configuration);

let updateRuleRequest: UpdateRuleRequest; //
let taskId: string; // (default to undefined)
let ruleId: string; // (default to undefined)

const { status, data } = await apiInstance.updateTaskRulesApiV2TasksTaskIdRulesRuleIdPatch(
    updateRuleRequest,
    taskId,
    ruleId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **updateRuleRequest** | **UpdateRuleRequest**|  | |
| **taskId** | [**string**] |  | defaults to undefined|
| **ruleId** | [**string**] |  | defaults to undefined|


### Return type

**TaskResponse**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

