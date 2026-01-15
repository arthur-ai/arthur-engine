# _generated.InferencesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**query_inferences_api_v2_inferences_query_get**](InferencesApi.md#query_inferences_api_v2_inferences_query_get) | **GET** /api/v2/inferences/query | Query Inferences


# **query_inferences_api_v2_inferences_query_get**
> QueryInferencesResponse query_inferences_api_v2_inferences_query_get(task_ids=task_ids, task_name=task_name, conversation_id=conversation_id, inference_id=inference_id, user_id=user_id, start_time=start_time, end_time=end_time, rule_types=rule_types, rule_statuses=rule_statuses, prompt_statuses=prompt_statuses, response_statuses=response_statuses, include_count=include_count, sort=sort, page_size=page_size, page=page)

Query Inferences

Paginated inference querying. See parameters for available filters. Includes inferences from archived tasks and rules.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.query_inferences_response import QueryInferencesResponse
from _generated.models.rule_result_enum import RuleResultEnum
from _generated.models.rule_type import RuleType
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
    api_instance = _generated.InferencesApi(api_client)
    task_ids = [] # List[Optional[str]] | Task ID to filter on. (optional) (default to [])
    task_name = 'task_name_example' # str | Task name to filter on. (optional)
    conversation_id = 'conversation_id_example' # str | Conversation ID to filter on. (optional)
    inference_id = 'inference_id_example' # str | Inference ID to filter on. (optional)
    user_id = 'user_id_example' # str | User ID to filter on. (optional)
    start_time = '2013-10-20T19:20:30+01:00' # datetime | Inclusive start date in ISO8601 string format. (optional)
    end_time = '2013-10-20T19:20:30+01:00' # datetime | Exclusive end date in ISO8601 string format. (optional)
    rule_types = [] # List[RuleType] | List of RuleType to query for. Any inference that ran any rule in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_statuses, will return inferences with rules in the intersection of rule_types and rule_statuses. (optional) (default to [])
    rule_statuses = [] # List[RuleResultEnum] | List of RuleResultEnum to query for. Any inference with any rule status in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_types, will return inferences with rules in the intersection of rule_statuses and rule_types. (optional) (default to [])
    prompt_statuses = [] # List[RuleResultEnum] | List of RuleResultEnum to query for at inference prompt stage level. Must be 'Pass' / 'Fail'. Defaults to both. (optional) (default to [])
    response_statuses = [] # List[RuleResultEnum] | List of RuleResultEnum to query for at inference response stage level. Must be 'Pass' / 'Fail'. Defaults to both. Inferences missing responses will not be affected by this filter. (optional) (default to [])
    include_count = True # bool | Whether to include the total count of matching inferences. Set to False to improve query performance for large datasets. Count will be returned as -1 if set to False. (optional) (default to True)
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Query Inferences
        api_response = api_instance.query_inferences_api_v2_inferences_query_get(task_ids=task_ids, task_name=task_name, conversation_id=conversation_id, inference_id=inference_id, user_id=user_id, start_time=start_time, end_time=end_time, rule_types=rule_types, rule_statuses=rule_statuses, prompt_statuses=prompt_statuses, response_statuses=response_statuses, include_count=include_count, sort=sort, page_size=page_size, page=page)
        print("The response of InferencesApi->query_inferences_api_v2_inferences_query_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling InferencesApi->query_inferences_api_v2_inferences_query_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_ids** | [**List[Optional[str]]**](str.md)| Task ID to filter on. | [optional] [default to []]
 **task_name** | **str**| Task name to filter on. | [optional] 
 **conversation_id** | **str**| Conversation ID to filter on. | [optional] 
 **inference_id** | **str**| Inference ID to filter on. | [optional] 
 **user_id** | **str**| User ID to filter on. | [optional] 
 **start_time** | **datetime**| Inclusive start date in ISO8601 string format. | [optional] 
 **end_time** | **datetime**| Exclusive end date in ISO8601 string format. | [optional] 
 **rule_types** | [**List[RuleType]**](RuleType.md)| List of RuleType to query for. Any inference that ran any rule in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_statuses, will return inferences with rules in the intersection of rule_types and rule_statuses. | [optional] [default to []]
 **rule_statuses** | [**List[RuleResultEnum]**](RuleResultEnum.md)| List of RuleResultEnum to query for. Any inference with any rule status in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_types, will return inferences with rules in the intersection of rule_statuses and rule_types. | [optional] [default to []]
 **prompt_statuses** | [**List[RuleResultEnum]**](RuleResultEnum.md)| List of RuleResultEnum to query for at inference prompt stage level. Must be &#39;Pass&#39; / &#39;Fail&#39;. Defaults to both. | [optional] [default to []]
 **response_statuses** | [**List[RuleResultEnum]**](RuleResultEnum.md)| List of RuleResultEnum to query for at inference response stage level. Must be &#39;Pass&#39; / &#39;Fail&#39;. Defaults to both. Inferences missing responses will not be affected by this filter. | [optional] [default to []]
 **include_count** | **bool**| Whether to include the total count of matching inferences. Set to False to improve query performance for large datasets. Count will be returned as -1 if set to False. | [optional] [default to True]
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**QueryInferencesResponse**](QueryInferencesResponse.md)

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

