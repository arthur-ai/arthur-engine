# arthur_observability_sdk._generated.ModelProvidersApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**delete_model_provider_api_v1_model_providers_provider_delete**](ModelProvidersApi.md#delete_model_provider_api_v1_model_providers_provider_delete) | **DELETE** /api/v1/model_providers/{provider} | Disables the configuration for a model provider.
[**get_model_providers_api_v1_model_providers_get**](ModelProvidersApi.md#get_model_providers_api_v1_model_providers_get) | **GET** /api/v1/model_providers | List the model providers.
[**get_model_providers_available_models_api_v1_model_providers_provider_available_models_get**](ModelProvidersApi.md#get_model_providers_available_models_api_v1_model_providers_provider_available_models_get) | **GET** /api/v1/model_providers/{provider}/available_models | List the models available from a provider.
[**set_model_provider_api_v1_model_providers_provider_put**](ModelProvidersApi.md#set_model_provider_api_v1_model_providers_provider_put) | **PUT** /api/v1/model_providers/{provider} | Set the configuration for a model provider.


# **delete_model_provider_api_v1_model_providers_provider_delete**
> delete_model_provider_api_v1_model_providers_provider_delete(provider)

Disables the configuration for a model provider.

Disables the configuration for a model provider

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.model_provider import ModelProvider
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
    api_instance = arthur_observability_sdk._generated.ModelProvidersApi(api_client)
    provider = arthur_observability_sdk._generated.ModelProvider() # ModelProvider | 

    try:
        # Disables the configuration for a model provider.
        api_instance.delete_model_provider_api_v1_model_providers_provider_delete(provider)
    except Exception as e:
        print("Exception when calling ModelProvidersApi->delete_model_provider_api_v1_model_providers_provider_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **provider** | [**ModelProvider**](.md)|  | 

### Return type

void (empty response body)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | Provider deleted. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_model_providers_api_v1_model_providers_get**
> ModelProviderList get_model_providers_api_v1_model_providers_get()

List the model providers.

Shows all model providers and if they're enabled.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.model_provider_list import ModelProviderList
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
    api_instance = arthur_observability_sdk._generated.ModelProvidersApi(api_client)

    try:
        # List the model providers.
        api_response = api_instance.get_model_providers_api_v1_model_providers_get()
        print("The response of ModelProvidersApi->get_model_providers_api_v1_model_providers_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ModelProvidersApi->get_model_providers_api_v1_model_providers_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**ModelProviderList**](ModelProviderList.md)

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

# **get_model_providers_available_models_api_v1_model_providers_provider_available_models_get**
> ModelProviderModelList get_model_providers_available_models_api_v1_model_providers_provider_available_models_get(provider)

List the models available from a provider.

Returns a list of the names of all available models for a provider.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.model_provider import ModelProvider
from arthur_observability_sdk._generated.models.model_provider_model_list import ModelProviderModelList
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
    api_instance = arthur_observability_sdk._generated.ModelProvidersApi(api_client)
    provider = arthur_observability_sdk._generated.ModelProvider() # ModelProvider | 

    try:
        # List the models available from a provider.
        api_response = api_instance.get_model_providers_available_models_api_v1_model_providers_provider_available_models_get(provider)
        print("The response of ModelProvidersApi->get_model_providers_available_models_api_v1_model_providers_provider_available_models_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ModelProvidersApi->get_model_providers_available_models_api_v1_model_providers_provider_available_models_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **provider** | [**ModelProvider**](.md)|  | 

### Return type

[**ModelProviderModelList**](ModelProviderModelList.md)

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

# **set_model_provider_api_v1_model_providers_provider_put**
> object set_model_provider_api_v1_model_providers_provider_put(provider, put_model_provider_credentials)

Set the configuration for a model provider.

Set the configuration for a model provider

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.model_provider import ModelProvider
from arthur_observability_sdk._generated.models.put_model_provider_credentials import PutModelProviderCredentials
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
    api_instance = arthur_observability_sdk._generated.ModelProvidersApi(api_client)
    provider = arthur_observability_sdk._generated.ModelProvider() # ModelProvider | 
    put_model_provider_credentials = arthur_observability_sdk._generated.PutModelProviderCredentials() # PutModelProviderCredentials | 

    try:
        # Set the configuration for a model provider.
        api_response = api_instance.set_model_provider_api_v1_model_providers_provider_put(provider, put_model_provider_credentials)
        print("The response of ModelProvidersApi->set_model_provider_api_v1_model_providers_provider_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ModelProvidersApi->set_model_provider_api_v1_model_providers_provider_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **provider** | [**ModelProvider**](.md)|  | 
 **put_model_provider_credentials** | [**PutModelProviderCredentials**](PutModelProviderCredentials.md)|  | 

### Return type

**object**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Configuration set |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

