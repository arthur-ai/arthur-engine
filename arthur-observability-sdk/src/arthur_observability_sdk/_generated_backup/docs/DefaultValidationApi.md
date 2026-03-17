# _generated.DefaultValidationApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**default_validate_prompt_api_v2_validate_prompt_post**](DefaultValidationApi.md#default_validate_prompt_api_v2_validate_prompt_post) | **POST** /api/v2/validate_prompt | Default Validate Prompt
[**default_validate_response_api_v2_validate_response_inference_id_post**](DefaultValidationApi.md#default_validate_response_api_v2_validate_response_inference_id_post) | **POST** /api/v2/validate_response/{inference_id} | Default Validate Response


# **default_validate_prompt_api_v2_validate_prompt_post**
> ValidationResult default_validate_prompt_api_v2_validate_prompt_post(prompt_validation_request)

Default Validate Prompt

[Deprecated] Validate a non-task related prompt based on the configured default rules.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.prompt_validation_request import PromptValidationRequest
from _generated.models.validation_result import ValidationResult
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
    api_instance = _generated.DefaultValidationApi(api_client)
    prompt_validation_request = _generated.PromptValidationRequest() # PromptValidationRequest | 

    try:
        # Default Validate Prompt
        api_response = api_instance.default_validate_prompt_api_v2_validate_prompt_post(prompt_validation_request)
        print("The response of DefaultValidationApi->default_validate_prompt_api_v2_validate_prompt_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultValidationApi->default_validate_prompt_api_v2_validate_prompt_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **prompt_validation_request** | [**PromptValidationRequest**](PromptValidationRequest.md)|  | 

### Return type

[**ValidationResult**](ValidationResult.md)

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

# **default_validate_response_api_v2_validate_response_inference_id_post**
> ValidationResult default_validate_response_api_v2_validate_response_inference_id_post(inference_id, response_validation_request)

Default Validate Response

[Deprecated] Validate a non-task related generated response based on the configured default rules. Inference ID corresponds to the previously validated associated prompt’s inference ID. Must provide context if a Hallucination Rule is an enabled default rule.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.response_validation_request import ResponseValidationRequest
from _generated.models.validation_result import ValidationResult
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
    api_instance = _generated.DefaultValidationApi(api_client)
    inference_id = 'inference_id_example' # str | 
    response_validation_request = _generated.ResponseValidationRequest() # ResponseValidationRequest | 

    try:
        # Default Validate Response
        api_response = api_instance.default_validate_response_api_v2_validate_response_inference_id_post(inference_id, response_validation_request)
        print("The response of DefaultValidationApi->default_validate_response_api_v2_validate_response_inference_id_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultValidationApi->default_validate_response_api_v2_validate_response_inference_id_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **inference_id** | **str**|  | 
 **response_validation_request** | [**ResponseValidationRequest**](ResponseValidationRequest.md)|  | 

### Return type

[**ValidationResult**](ValidationResult.md)

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

