# arthur_observability_sdk._generated.TaskBasedValidationApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**validate_prompt_endpoint_api_v2_tasks_task_id_validate_prompt_post**](TaskBasedValidationApi.md#validate_prompt_endpoint_api_v2_tasks_task_id_validate_prompt_post) | **POST** /api/v2/tasks/{task_id}/validate_prompt | Validate Prompt Endpoint
[**validate_response_endpoint_api_v2_tasks_task_id_validate_response_inference_id_post**](TaskBasedValidationApi.md#validate_response_endpoint_api_v2_tasks_task_id_validate_response_inference_id_post) | **POST** /api/v2/tasks/{task_id}/validate_response/{inference_id} | Validate Response Endpoint


# **validate_prompt_endpoint_api_v2_tasks_task_id_validate_prompt_post**
> ValidationResult validate_prompt_endpoint_api_v2_tasks_task_id_validate_prompt_post(task_id, prompt_validation_request)

Validate Prompt Endpoint

Validate a prompt based on the configured rules for this task. Note: Rules related to specific tasks are cached for 60 seconds.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.prompt_validation_request import PromptValidationRequest
from arthur_observability_sdk._generated.models.validation_result import ValidationResult
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
    api_instance = arthur_observability_sdk._generated.TaskBasedValidationApi(api_client)
    task_id = 'task_id_example' # str | 
    prompt_validation_request = arthur_observability_sdk._generated.PromptValidationRequest() # PromptValidationRequest | 

    try:
        # Validate Prompt Endpoint
        api_response = api_instance.validate_prompt_endpoint_api_v2_tasks_task_id_validate_prompt_post(task_id, prompt_validation_request)
        print("The response of TaskBasedValidationApi->validate_prompt_endpoint_api_v2_tasks_task_id_validate_prompt_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TaskBasedValidationApi->validate_prompt_endpoint_api_v2_tasks_task_id_validate_prompt_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
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
**400** | Bad Request |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **validate_response_endpoint_api_v2_tasks_task_id_validate_response_inference_id_post**
> ValidationResult validate_response_endpoint_api_v2_tasks_task_id_validate_response_inference_id_post(inference_id, task_id, response_validation_request)

Validate Response Endpoint

Validate a response based on the configured rules for this task. Inference ID corresponds to the previously validated associated prompt’s inference id. Must provide context if a Hallucination Rule is an enabled task rule. Note: Rules related to specific tasks are cached for 60 seconds.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.response_validation_request import ResponseValidationRequest
from arthur_observability_sdk._generated.models.validation_result import ValidationResult
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
    api_instance = arthur_observability_sdk._generated.TaskBasedValidationApi(api_client)
    inference_id = 'inference_id_example' # str | 
    task_id = 'task_id_example' # str | 
    response_validation_request = arthur_observability_sdk._generated.ResponseValidationRequest() # ResponseValidationRequest | 

    try:
        # Validate Response Endpoint
        api_response = api_instance.validate_response_endpoint_api_v2_tasks_task_id_validate_response_inference_id_post(inference_id, task_id, response_validation_request)
        print("The response of TaskBasedValidationApi->validate_response_endpoint_api_v2_tasks_task_id_validate_response_inference_id_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling TaskBasedValidationApi->validate_response_endpoint_api_v2_tasks_task_id_validate_response_inference_id_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **inference_id** | **str**|  | 
 **task_id** | **str**|  | 
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
**400** | Bad Request |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

