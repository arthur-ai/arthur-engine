# _generated.SecretsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**rotate_secrets_api_v1_secrets_rotation_post**](SecretsApi.md#rotate_secrets_api_v1_secrets_rotation_post) | **POST** /api/v1/secrets/rotation | Rotates secrets


# **rotate_secrets_api_v1_secrets_rotation_post**
> rotate_secrets_api_v1_secrets_rotation_post()

Rotates secrets

This endpoint re-encrypts all the secrets in the database. The procedure calling this endpoint is as follows: 
First: Deploy a new version of the service with GENAI_ENGINE_SECRET_STORE_KEY set to a value like 'new-key::old-key'. 
Second: call this endpoint - all secrets will be re-encrypted with 'new-key'. 
Third: Deploy a new version of the service removing the old key from GENAI_ENGINE_SECRET_STORE_KEY, like 'new-key'. 
At this point all existing and new secrets will be managed by 'new-key'.

### Example

* Bearer Authentication (API Key):

```python
import _generated
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
    api_instance = _generated.SecretsApi(api_client)

    try:
        # Rotates secrets
        api_instance.rotate_secrets_api_v1_secrets_rotation_post()
    except Exception as e:
        print("Exception when calling SecretsApi->rotate_secrets_api_v1_secrets_rotation_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | Secrets rotated. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

