# _generated.APIKeysApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_api_key_auth_api_keys_post**](APIKeysApi.md#create_api_key_auth_api_keys_post) | **POST** /auth/api_keys/ | Create Api Key
[**deactivate_api_key_auth_api_keys_deactivate_api_key_id_delete**](APIKeysApi.md#deactivate_api_key_auth_api_keys_deactivate_api_key_id_delete) | **DELETE** /auth/api_keys/deactivate/{api_key_id} | Deactivate Api Key
[**get_all_active_api_keys_auth_api_keys_get**](APIKeysApi.md#get_all_active_api_keys_auth_api_keys_get) | **GET** /auth/api_keys/ | Get All Active Api Keys
[**get_api_key_auth_api_keys_api_key_id_get**](APIKeysApi.md#get_api_key_auth_api_keys_api_key_id_get) | **GET** /auth/api_keys/{api_key_id} | Get Api Key


# **create_api_key_auth_api_keys_post**
> ApiKeyResponse create_api_key_auth_api_keys_post(new_api_key_request)

Create Api Key

Generates a new API key. Up to 1000 active keys can exist at the same time by default. Contact your system administrator if you need more. Allowed roles are: DEFAULT-RULE-ADMIN, TASK-ADMIN, VALIDATION-USER, ORG-AUDITOR, ORG-ADMIN.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.api_key_response import ApiKeyResponse
from _generated.models.new_api_key_request import NewApiKeyRequest
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
    api_instance = _generated.APIKeysApi(api_client)
    new_api_key_request = _generated.NewApiKeyRequest() # NewApiKeyRequest | 

    try:
        # Create Api Key
        api_response = api_instance.create_api_key_auth_api_keys_post(new_api_key_request)
        print("The response of APIKeysApi->create_api_key_auth_api_keys_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling APIKeysApi->create_api_key_auth_api_keys_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **new_api_key_request** | [**NewApiKeyRequest**](NewApiKeyRequest.md)|  | 

### Return type

[**ApiKeyResponse**](ApiKeyResponse.md)

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

# **deactivate_api_key_auth_api_keys_deactivate_api_key_id_delete**
> ApiKeyResponse deactivate_api_key_auth_api_keys_deactivate_api_key_id_delete(api_key_id)

Deactivate Api Key

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.api_key_response import ApiKeyResponse
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
    api_instance = _generated.APIKeysApi(api_client)
    api_key_id = 'api_key_id_example' # str | 

    try:
        # Deactivate Api Key
        api_response = api_instance.deactivate_api_key_auth_api_keys_deactivate_api_key_id_delete(api_key_id)
        print("The response of APIKeysApi->deactivate_api_key_auth_api_keys_deactivate_api_key_id_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling APIKeysApi->deactivate_api_key_auth_api_keys_deactivate_api_key_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **api_key_id** | **str**|  | 

### Return type

[**ApiKeyResponse**](ApiKeyResponse.md)

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

# **get_all_active_api_keys_auth_api_keys_get**
> List[ApiKeyResponse] get_all_active_api_keys_auth_api_keys_get()

Get All Active Api Keys

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.api_key_response import ApiKeyResponse
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
    api_instance = _generated.APIKeysApi(api_client)

    try:
        # Get All Active Api Keys
        api_response = api_instance.get_all_active_api_keys_auth_api_keys_get()
        print("The response of APIKeysApi->get_all_active_api_keys_auth_api_keys_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling APIKeysApi->get_all_active_api_keys_auth_api_keys_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**List[ApiKeyResponse]**](ApiKeyResponse.md)

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

# **get_api_key_auth_api_keys_api_key_id_get**
> ApiKeyResponse get_api_key_auth_api_keys_api_key_id_get(api_key_id)

Get Api Key

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.api_key_response import ApiKeyResponse
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
    api_instance = _generated.APIKeysApi(api_client)
    api_key_id = 'api_key_id_example' # str | 

    try:
        # Get Api Key
        api_response = api_instance.get_api_key_auth_api_keys_api_key_id_get(api_key_id)
        print("The response of APIKeysApi->get_api_key_auth_api_keys_api_key_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling APIKeysApi->get_api_key_auth_api_keys_api_key_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **api_key_id** | **str**|  | 

### Return type

[**ApiKeyResponse**](ApiKeyResponse.md)

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

