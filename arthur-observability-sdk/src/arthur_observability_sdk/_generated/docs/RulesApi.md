# arthur_observability_sdk._generated.RulesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**archive_default_rule_api_v2_default_rules_rule_id_delete**](RulesApi.md#archive_default_rule_api_v2_default_rules_rule_id_delete) | **DELETE** /api/v2/default_rules/{rule_id} | Archive Default Rule
[**create_default_rule_api_v2_default_rules_post**](RulesApi.md#create_default_rule_api_v2_default_rules_post) | **POST** /api/v2/default_rules | Create Default Rule
[**get_default_rules_api_v2_default_rules_get**](RulesApi.md#get_default_rules_api_v2_default_rules_get) | **GET** /api/v2/default_rules | Get Default Rules
[**search_rules_api_v2_rules_search_post**](RulesApi.md#search_rules_api_v2_rules_search_post) | **POST** /api/v2/rules/search | Search Rules


# **archive_default_rule_api_v2_default_rules_rule_id_delete**
> object archive_default_rule_api_v2_default_rules_rule_id_delete(rule_id)

Archive Default Rule

Archive existing default rule.

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
    api_instance = arthur_observability_sdk._generated.RulesApi(api_client)
    rule_id = 'rule_id_example' # str | 

    try:
        # Archive Default Rule
        api_response = api_instance.archive_default_rule_api_v2_default_rules_rule_id_delete(rule_id)
        print("The response of RulesApi->archive_default_rule_api_v2_default_rules_rule_id_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RulesApi->archive_default_rule_api_v2_default_rules_rule_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **rule_id** | **str**|  | 

### Return type

**object**

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

# **create_default_rule_api_v2_default_rules_post**
> RuleResponse create_default_rule_api_v2_default_rules_post(new_rule_request=new_rule_request)

Create Default Rule

Create a default rule. Default rules are applied universally across existing tasks, subsequently created new tasks, and any non-task related requests. Once a rule is created, it is immutable. Available rules are 'KeywordRule', 'ModelHallucinationRuleV2', 'ModelSensitiveDataRule', 'PIIDataRule', 'PromptInjectionRule', 'RegexRule', 'ToxicityRule'. Note: The rules are cached by the validation endpoints for 60 seconds.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.new_rule_request import NewRuleRequest
from arthur_observability_sdk._generated.models.rule_response import RuleResponse
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
    api_instance = arthur_observability_sdk._generated.RulesApi(api_client)
    new_rule_request = {"name":"Sensitive Data Rule","type":"ModelSensitiveDataRule","apply_to_prompt":true,"apply_to_response":false,"config":{"examples":[{"example":"John has O negative blood group","result":true},{"example":"Most of the people have A positive blood group","result":false}],"hint":"specific individual's blood types"}} # NewRuleRequest |  (optional)

    try:
        # Create Default Rule
        api_response = api_instance.create_default_rule_api_v2_default_rules_post(new_rule_request=new_rule_request)
        print("The response of RulesApi->create_default_rule_api_v2_default_rules_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RulesApi->create_default_rule_api_v2_default_rules_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **new_rule_request** | [**NewRuleRequest**](NewRuleRequest.md)|  | [optional] 

### Return type

[**RuleResponse**](RuleResponse.md)

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

# **get_default_rules_api_v2_default_rules_get**
> List[RuleResponse] get_default_rules_api_v2_default_rules_get()

Get Default Rules

Get default rules.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.rule_response import RuleResponse
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
    api_instance = arthur_observability_sdk._generated.RulesApi(api_client)

    try:
        # Get Default Rules
        api_response = api_instance.get_default_rules_api_v2_default_rules_get()
        print("The response of RulesApi->get_default_rules_api_v2_default_rules_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RulesApi->get_default_rules_api_v2_default_rules_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**List[RuleResponse]**](RuleResponse.md)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **search_rules_api_v2_rules_search_post**
> SearchRulesResponse search_rules_api_v2_rules_search_post(search_rules_request, sort=sort, page_size=page_size, page=page)

Search Rules

Search default and/or task rules.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.search_rules_request import SearchRulesRequest
from arthur_observability_sdk._generated.models.search_rules_response import SearchRulesResponse
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
    api_instance = arthur_observability_sdk._generated.RulesApi(api_client)
    search_rules_request = arthur_observability_sdk._generated.SearchRulesRequest() # SearchRulesRequest | 
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Search Rules
        api_response = api_instance.search_rules_api_v2_rules_search_post(search_rules_request, sort=sort, page_size=page_size, page=page)
        print("The response of RulesApi->search_rules_api_v2_rules_search_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RulesApi->search_rules_api_v2_rules_search_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **search_rules_request** | [**SearchRulesRequest**](SearchRulesRequest.md)|  | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**SearchRulesResponse**](SearchRulesResponse.md)

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

