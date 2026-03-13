# _generated.UsageApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_token_usage_api_v2_usage_tokens_get**](UsageApi.md#get_token_usage_api_v2_usage_tokens_get) | **GET** /api/v2/usage/tokens | Get Token Usage


# **get_token_usage_api_v2_usage_tokens_get**
> List[TokenUsageResponse] get_token_usage_api_v2_usage_tokens_get(start_time=start_time, end_time=end_time, group_by=group_by)

Get Token Usage

Get token usage.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.token_usage_response import TokenUsageResponse
from _generated.models.token_usage_scope import TokenUsageScope
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
    api_instance = _generated.UsageApi(api_client)
    start_time = '2013-10-20T19:20:30+01:00' # datetime | Inclusive start date in ISO8601 string format. Defaults to the beginning of the current day if not provided. (optional)
    end_time = '2013-10-20T19:20:30+01:00' # datetime | Exclusive end date in ISO8601 string format. Defaults to the end of the current day if not provided. (optional)
    group_by = ["rule_type"] # List[TokenUsageScope] | Entities to group token counts on. (optional) (default to ["rule_type"])

    try:
        # Get Token Usage
        api_response = api_instance.get_token_usage_api_v2_usage_tokens_get(start_time=start_time, end_time=end_time, group_by=group_by)
        print("The response of UsageApi->get_token_usage_api_v2_usage_tokens_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling UsageApi->get_token_usage_api_v2_usage_tokens_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **start_time** | **datetime**| Inclusive start date in ISO8601 string format. Defaults to the beginning of the current day if not provided. | [optional] 
 **end_time** | **datetime**| Exclusive end date in ISO8601 string format. Defaults to the end of the current day if not provided. | [optional] 
 **group_by** | [**List[TokenUsageScope]**](TokenUsageScope.md)| Entities to group token counts on. | [optional] [default to [&quot;rule_type&quot;]]

### Return type

[**List[TokenUsageResponse]**](TokenUsageResponse.md)

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

