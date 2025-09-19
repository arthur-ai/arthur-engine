# InferencesApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**queryInferencesApiV2InferencesQueryGet**](#queryinferencesapiv2inferencesqueryget) | **GET** /api/v2/inferences/query | Query Inferences|

# **queryInferencesApiV2InferencesQueryGet**
> QueryInferencesResponse queryInferencesApiV2InferencesQueryGet()

Paginated inference querying. See parameters for available filters. Includes inferences from archived tasks and rules.

### Example

```typescript
import {
    InferencesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new InferencesApi(configuration);

let taskIds: Array<string>; //Task ID to filter on. (optional) (default to undefined)
let taskName: string; //Task name to filter on. (optional) (default to undefined)
let conversationId: string; //Conversation ID to filter on. (optional) (default to undefined)
let inferenceId: string; //Inference ID to filter on. (optional) (default to undefined)
let userId: string; //User ID to filter on. (optional) (default to undefined)
let startTime: string; //Inclusive start date in ISO8601 string format. (optional) (default to undefined)
let endTime: string; //Exclusive end date in ISO8601 string format. (optional) (default to undefined)
let ruleTypes: Array<RuleType>; //List of RuleType to query for. Any inference that ran any rule in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_statuses, will return inferences with rules in the intersection of rule_types and rule_statuses. (optional) (default to undefined)
let ruleStatuses: Array<RuleResultEnum>; //List of RuleResultEnum to query for. Any inference with any rule status in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_types, will return inferences with rules in the intersection of rule_statuses and rule_types. (optional) (default to undefined)
let promptStatuses: Array<RuleResultEnum>; //List of RuleResultEnum to query for at inference prompt stage level. Must be \'Pass\' / \'Fail\'. Defaults to both. (optional) (default to undefined)
let responseStatuses: Array<RuleResultEnum>; //List of RuleResultEnum to query for at inference response stage level. Must be \'Pass\' / \'Fail\'. Defaults to both. Inferences missing responses will not be affected by this filter. (optional) (default to undefined)
let includeCount: boolean; //Whether to include the total count of matching inferences. Set to False to improve query performance for large datasets. Count will be returned as -1 if set to False. (optional) (default to true)
let sort: PaginationSortMethod; //Sort the results (asc/desc) (optional) (default to undefined)
let pageSize: number; //Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
let page: number; //Page number (optional) (default to 0)

const { status, data } = await apiInstance.queryInferencesApiV2InferencesQueryGet(
    taskIds,
    taskName,
    conversationId,
    inferenceId,
    userId,
    startTime,
    endTime,
    ruleTypes,
    ruleStatuses,
    promptStatuses,
    responseStatuses,
    includeCount,
    sort,
    pageSize,
    page
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **taskIds** | **Array&lt;string&gt;** | Task ID to filter on. | (optional) defaults to undefined|
| **taskName** | [**string**] | Task name to filter on. | (optional) defaults to undefined|
| **conversationId** | [**string**] | Conversation ID to filter on. | (optional) defaults to undefined|
| **inferenceId** | [**string**] | Inference ID to filter on. | (optional) defaults to undefined|
| **userId** | [**string**] | User ID to filter on. | (optional) defaults to undefined|
| **startTime** | [**string**] | Inclusive start date in ISO8601 string format. | (optional) defaults to undefined|
| **endTime** | [**string**] | Exclusive end date in ISO8601 string format. | (optional) defaults to undefined|
| **ruleTypes** | **Array&lt;RuleType&gt;** | List of RuleType to query for. Any inference that ran any rule in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_statuses, will return inferences with rules in the intersection of rule_types and rule_statuses. | (optional) defaults to undefined|
| **ruleStatuses** | **Array&lt;RuleResultEnum&gt;** | List of RuleResultEnum to query for. Any inference with any rule status in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_types, will return inferences with rules in the intersection of rule_statuses and rule_types. | (optional) defaults to undefined|
| **promptStatuses** | **Array&lt;RuleResultEnum&gt;** | List of RuleResultEnum to query for at inference prompt stage level. Must be \&#39;Pass\&#39; / \&#39;Fail\&#39;. Defaults to both. | (optional) defaults to undefined|
| **responseStatuses** | **Array&lt;RuleResultEnum&gt;** | List of RuleResultEnum to query for at inference response stage level. Must be \&#39;Pass\&#39; / \&#39;Fail\&#39;. Defaults to both. Inferences missing responses will not be affected by this filter. | (optional) defaults to undefined|
| **includeCount** | [**boolean**] | Whether to include the total count of matching inferences. Set to False to improve query performance for large datasets. Count will be returned as -1 if set to False. | (optional) defaults to true|
| **sort** | **PaginationSortMethod** | Sort the results (asc/desc) | (optional) defaults to undefined|
| **pageSize** | [**number**] | Page size. Default is 10. Must be greater than 0 and less than 5000. | (optional) defaults to 10|
| **page** | [**number**] | Page number | (optional) defaults to 0|


### Return type

**QueryInferencesResponse**

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

