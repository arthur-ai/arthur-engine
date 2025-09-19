# RulesApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**archiveDefaultRuleApiV2DefaultRulesRuleIdDelete**](#archivedefaultruleapiv2defaultrulesruleiddelete) | **DELETE** /api/v2/default_rules/{rule_id} | Archive Default Rule|
|[**createDefaultRuleApiV2DefaultRulesPost**](#createdefaultruleapiv2defaultrulespost) | **POST** /api/v2/default_rules | Create Default Rule|
|[**getDefaultRulesApiV2DefaultRulesGet**](#getdefaultrulesapiv2defaultrulesget) | **GET** /api/v2/default_rules | Get Default Rules|
|[**searchRulesApiV2RulesSearchPost**](#searchrulesapiv2rulessearchpost) | **POST** /api/v2/rules/search | Search Rules|

# **archiveDefaultRuleApiV2DefaultRulesRuleIdDelete**
> any archiveDefaultRuleApiV2DefaultRulesRuleIdDelete()

Archive existing default rule.

### Example

```typescript
import {
    RulesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new RulesApi(configuration);

let ruleId: string; // (default to undefined)

const { status, data } = await apiInstance.archiveDefaultRuleApiV2DefaultRulesRuleIdDelete(
    ruleId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
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

# **createDefaultRuleApiV2DefaultRulesPost**
> RuleResponse createDefaultRuleApiV2DefaultRulesPost()

Create a default rule. Default rules are applied universally across existing tasks, subsequently created new tasks, and any non-task related requests. Once a rule is created, it is immutable. Available rules are \'KeywordRule\', \'ModelHallucinationRuleV2\', \'ModelSensitiveDataRule\', \'PIIDataRule\', \'PromptInjectionRule\', \'RegexRule\', \'ToxicityRule\'. Note: The rules are cached by the validation endpoints for 60 seconds.

### Example

```typescript
import {
    RulesApi,
    Configuration,
    NewRuleRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new RulesApi(configuration);

let newRuleRequest: NewRuleRequest; // (optional)

const { status, data } = await apiInstance.createDefaultRuleApiV2DefaultRulesPost(
    newRuleRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **newRuleRequest** | **NewRuleRequest**|  | |


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

# **getDefaultRulesApiV2DefaultRulesGet**
> Array<RuleResponse> getDefaultRulesApiV2DefaultRulesGet()

Get default rules.

### Example

```typescript
import {
    RulesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new RulesApi(configuration);

const { status, data } = await apiInstance.getDefaultRulesApiV2DefaultRulesGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**Array<RuleResponse>**

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

# **searchRulesApiV2RulesSearchPost**
> SearchRulesResponse searchRulesApiV2RulesSearchPost(searchRulesRequest)

Search default and/or task rules.

### Example

```typescript
import {
    RulesApi,
    Configuration,
    SearchRulesRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new RulesApi(configuration);

let searchRulesRequest: SearchRulesRequest; //
let sort: PaginationSortMethod; //Sort the results (asc/desc) (optional) (default to undefined)
let pageSize: number; //Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
let page: number; //Page number (optional) (default to 0)

const { status, data } = await apiInstance.searchRulesApiV2RulesSearchPost(
    searchRulesRequest,
    sort,
    pageSize,
    page
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **searchRulesRequest** | **SearchRulesRequest**|  | |
| **sort** | **PaginationSortMethod** | Sort the results (asc/desc) | (optional) defaults to undefined|
| **pageSize** | [**number**] | Page size. Default is 10. Must be greater than 0 and less than 5000. | (optional) defaults to 10|
| **page** | [**number**] | Page number | (optional) defaults to 0|


### Return type

**SearchRulesResponse**

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

