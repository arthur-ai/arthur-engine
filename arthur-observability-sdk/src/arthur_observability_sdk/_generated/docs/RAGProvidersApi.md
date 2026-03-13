# arthur_observability_sdk._generated.RAGProvidersApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_rag_provider_api_v1_tasks_task_id_rag_providers_post**](RAGProvidersApi.md#create_rag_provider_api_v1_tasks_task_id_rag_providers_post) | **POST** /api/v1/tasks/{task_id}/rag_providers | Create Rag Provider
[**delete_rag_provider_api_v1_rag_providers_provider_id_delete**](RAGProvidersApi.md#delete_rag_provider_api_v1_rag_providers_provider_id_delete) | **DELETE** /api/v1/rag_providers/{provider_id} | Delete Rag Provider
[**execute_hybrid_search_api_v1_rag_providers_provider_id_hybrid_search_post**](RAGProvidersApi.md#execute_hybrid_search_api_v1_rag_providers_provider_id_hybrid_search_post) | **POST** /api/v1/rag_providers/{provider_id}/hybrid_search | Execute Hybrid Search
[**execute_keyword_search_api_v1_rag_providers_provider_id_keyword_search_post**](RAGProvidersApi.md#execute_keyword_search_api_v1_rag_providers_provider_id_keyword_search_post) | **POST** /api/v1/rag_providers/{provider_id}/keyword_search | Execute Keyword Search
[**execute_similarity_text_search_api_v1_rag_providers_provider_id_similarity_text_search_post**](RAGProvidersApi.md#execute_similarity_text_search_api_v1_rag_providers_provider_id_similarity_text_search_post) | **POST** /api/v1/rag_providers/{provider_id}/similarity_text_search | Execute Similarity Text Search
[**get_rag_provider_api_v1_rag_providers_provider_id_get**](RAGProvidersApi.md#get_rag_provider_api_v1_rag_providers_provider_id_get) | **GET** /api/v1/rag_providers/{provider_id} | Get Rag Provider
[**get_rag_providers_api_v1_tasks_task_id_rag_providers_get**](RAGProvidersApi.md#get_rag_providers_api_v1_tasks_task_id_rag_providers_get) | **GET** /api/v1/tasks/{task_id}/rag_providers | Get Rag Providers
[**list_rag_provider_collections_api_v1_rag_providers_provider_id_collections_get**](RAGProvidersApi.md#list_rag_provider_collections_api_v1_rag_providers_provider_id_collections_get) | **GET** /api/v1/rag_providers/{provider_id}/collections | List Rag Provider Collections
[**test_rag_provider_connection_api_v1_tasks_task_id_rag_providers_test_connection_post**](RAGProvidersApi.md#test_rag_provider_connection_api_v1_tasks_task_id_rag_providers_test_connection_post) | **POST** /api/v1/tasks/{task_id}/rag_providers/test_connection | Test Rag Provider Connection
[**update_rag_provider_api_v1_rag_providers_provider_id_patch**](RAGProvidersApi.md#update_rag_provider_api_v1_rag_providers_provider_id_patch) | **PATCH** /api/v1/rag_providers/{provider_id} | Update Rag Provider


# **create_rag_provider_api_v1_tasks_task_id_rag_providers_post**
> RagProviderConfigurationResponse create_rag_provider_api_v1_tasks_task_id_rag_providers_post(task_id, rag_provider_configuration_request)

Create Rag Provider

Register a new RAG provider connection configuration.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.rag_provider_configuration_request import RagProviderConfigurationRequest
from arthur_observability_sdk._generated.models.rag_provider_configuration_response import RagProviderConfigurationResponse
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
    api_instance = arthur_observability_sdk._generated.RAGProvidersApi(api_client)
    task_id = 'task_id_example' # str | ID of the task to register a new provider connection for. Should be formatted as a UUID.
    rag_provider_configuration_request = arthur_observability_sdk._generated.RagProviderConfigurationRequest() # RagProviderConfigurationRequest | 

    try:
        # Create Rag Provider
        api_response = api_instance.create_rag_provider_api_v1_tasks_task_id_rag_providers_post(task_id, rag_provider_configuration_request)
        print("The response of RAGProvidersApi->create_rag_provider_api_v1_tasks_task_id_rag_providers_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGProvidersApi->create_rag_provider_api_v1_tasks_task_id_rag_providers_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**| ID of the task to register a new provider connection for. Should be formatted as a UUID. | 
 **rag_provider_configuration_request** | [**RagProviderConfigurationRequest**](RagProviderConfigurationRequest.md)|  | 

### Return type

[**RagProviderConfigurationResponse**](RagProviderConfigurationResponse.md)

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

# **delete_rag_provider_api_v1_rag_providers_provider_id_delete**
> delete_rag_provider_api_v1_rag_providers_provider_id_delete(provider_id)

Delete Rag Provider

Delete a RAG provider connection configuration.

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
    api_instance = arthur_observability_sdk._generated.RAGProvidersApi(api_client)
    provider_id = 'provider_id_example' # str | ID of the RAG provider configuration to delete.

    try:
        # Delete Rag Provider
        api_instance.delete_rag_provider_api_v1_rag_providers_provider_id_delete(provider_id)
    except Exception as e:
        print("Exception when calling RAGProvidersApi->delete_rag_provider_api_v1_rag_providers_provider_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **provider_id** | **str**| ID of the RAG provider configuration to delete. | 

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
**204** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **execute_hybrid_search_api_v1_rag_providers_provider_id_hybrid_search_post**
> RagProviderQueryResponse execute_hybrid_search_api_v1_rag_providers_provider_id_hybrid_search_post(provider_id, rag_hybrid_search_setting_request)

Execute Hybrid Search

Execute a RAG provider hybrid (keyword and vector similarity) search.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.rag_hybrid_search_setting_request import RagHybridSearchSettingRequest
from arthur_observability_sdk._generated.models.rag_provider_query_response import RagProviderQueryResponse
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
    api_instance = arthur_observability_sdk._generated.RAGProvidersApi(api_client)
    provider_id = 'provider_id_example' # str | ID of the RAG provider configuration to use for the vector database connection.
    rag_hybrid_search_setting_request = arthur_observability_sdk._generated.RagHybridSearchSettingRequest() # RagHybridSearchSettingRequest | 

    try:
        # Execute Hybrid Search
        api_response = api_instance.execute_hybrid_search_api_v1_rag_providers_provider_id_hybrid_search_post(provider_id, rag_hybrid_search_setting_request)
        print("The response of RAGProvidersApi->execute_hybrid_search_api_v1_rag_providers_provider_id_hybrid_search_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGProvidersApi->execute_hybrid_search_api_v1_rag_providers_provider_id_hybrid_search_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **provider_id** | **str**| ID of the RAG provider configuration to use for the vector database connection. | 
 **rag_hybrid_search_setting_request** | [**RagHybridSearchSettingRequest**](RagHybridSearchSettingRequest.md)|  | 

### Return type

[**RagProviderQueryResponse**](RagProviderQueryResponse.md)

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

# **execute_keyword_search_api_v1_rag_providers_provider_id_keyword_search_post**
> RagProviderQueryResponse execute_keyword_search_api_v1_rag_providers_provider_id_keyword_search_post(provider_id, rag_keyword_search_setting_request)

Execute Keyword Search

Execute a RAG Provider Keyword (BM25/Sparse Vector) Search.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.rag_keyword_search_setting_request import RagKeywordSearchSettingRequest
from arthur_observability_sdk._generated.models.rag_provider_query_response import RagProviderQueryResponse
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
    api_instance = arthur_observability_sdk._generated.RAGProvidersApi(api_client)
    provider_id = 'provider_id_example' # str | ID of the RAG provider configuration to use for the vector database connection.
    rag_keyword_search_setting_request = arthur_observability_sdk._generated.RagKeywordSearchSettingRequest() # RagKeywordSearchSettingRequest | 

    try:
        # Execute Keyword Search
        api_response = api_instance.execute_keyword_search_api_v1_rag_providers_provider_id_keyword_search_post(provider_id, rag_keyword_search_setting_request)
        print("The response of RAGProvidersApi->execute_keyword_search_api_v1_rag_providers_provider_id_keyword_search_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGProvidersApi->execute_keyword_search_api_v1_rag_providers_provider_id_keyword_search_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **provider_id** | **str**| ID of the RAG provider configuration to use for the vector database connection. | 
 **rag_keyword_search_setting_request** | [**RagKeywordSearchSettingRequest**](RagKeywordSearchSettingRequest.md)|  | 

### Return type

[**RagProviderQueryResponse**](RagProviderQueryResponse.md)

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

# **execute_similarity_text_search_api_v1_rag_providers_provider_id_similarity_text_search_post**
> RagProviderQueryResponse execute_similarity_text_search_api_v1_rag_providers_provider_id_similarity_text_search_post(provider_id, rag_vector_similarity_text_search_setting_request)

Execute Similarity Text Search

Execute a RAG Provider Similarity Text Search.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.rag_provider_query_response import RagProviderQueryResponse
from arthur_observability_sdk._generated.models.rag_vector_similarity_text_search_setting_request import RagVectorSimilarityTextSearchSettingRequest
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
    api_instance = arthur_observability_sdk._generated.RAGProvidersApi(api_client)
    provider_id = 'provider_id_example' # str | ID of the RAG provider configuration to use for the vector database connection.
    rag_vector_similarity_text_search_setting_request = arthur_observability_sdk._generated.RagVectorSimilarityTextSearchSettingRequest() # RagVectorSimilarityTextSearchSettingRequest | 

    try:
        # Execute Similarity Text Search
        api_response = api_instance.execute_similarity_text_search_api_v1_rag_providers_provider_id_similarity_text_search_post(provider_id, rag_vector_similarity_text_search_setting_request)
        print("The response of RAGProvidersApi->execute_similarity_text_search_api_v1_rag_providers_provider_id_similarity_text_search_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGProvidersApi->execute_similarity_text_search_api_v1_rag_providers_provider_id_similarity_text_search_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **provider_id** | **str**| ID of the RAG provider configuration to use for the vector database connection. | 
 **rag_vector_similarity_text_search_setting_request** | [**RagVectorSimilarityTextSearchSettingRequest**](RagVectorSimilarityTextSearchSettingRequest.md)|  | 

### Return type

[**RagProviderQueryResponse**](RagProviderQueryResponse.md)

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

# **get_rag_provider_api_v1_rag_providers_provider_id_get**
> RagProviderConfigurationResponse get_rag_provider_api_v1_rag_providers_provider_id_get(provider_id)

Get Rag Provider

Get a single RAG provider connection configuration.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.rag_provider_configuration_response import RagProviderConfigurationResponse
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
    api_instance = arthur_observability_sdk._generated.RAGProvidersApi(api_client)
    provider_id = 'provider_id_example' # str | ID of RAG provider configuration.

    try:
        # Get Rag Provider
        api_response = api_instance.get_rag_provider_api_v1_rag_providers_provider_id_get(provider_id)
        print("The response of RAGProvidersApi->get_rag_provider_api_v1_rag_providers_provider_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGProvidersApi->get_rag_provider_api_v1_rag_providers_provider_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **provider_id** | **str**| ID of RAG provider configuration. | 

### Return type

[**RagProviderConfigurationResponse**](RagProviderConfigurationResponse.md)

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

# **get_rag_providers_api_v1_tasks_task_id_rag_providers_get**
> SearchRagProviderConfigurationsResponse get_rag_providers_api_v1_tasks_task_id_rag_providers_get(task_id, config_name=config_name, authentication_method=authentication_method, rag_provider_name=rag_provider_name, sort=sort, page_size=page_size, page=page)

Get Rag Providers

Get list of RAG provider connection configurations for the task.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.rag_api_key_authentication_provider_enum import RagAPIKeyAuthenticationProviderEnum
from arthur_observability_sdk._generated.models.rag_provider_authentication_method_enum import RagProviderAuthenticationMethodEnum
from arthur_observability_sdk._generated.models.search_rag_provider_configurations_response import SearchRagProviderConfigurationsResponse
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
    api_instance = arthur_observability_sdk._generated.RAGProvidersApi(api_client)
    task_id = 'task_id_example' # str | ID of the task to fetch the provider connections for.
    config_name = 'config_name_example' # str | RAG Provider configuration name substring to search for. (optional)
    authentication_method = arthur_observability_sdk._generated.RagProviderAuthenticationMethodEnum() # RagProviderAuthenticationMethodEnum | RAG Provider authentication method to filter by. (optional)
    rag_provider_name = arthur_observability_sdk._generated.RagAPIKeyAuthenticationProviderEnum() # RagAPIKeyAuthenticationProviderEnum | RAG provider name to filter by. (optional)
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get Rag Providers
        api_response = api_instance.get_rag_providers_api_v1_tasks_task_id_rag_providers_get(task_id, config_name=config_name, authentication_method=authentication_method, rag_provider_name=rag_provider_name, sort=sort, page_size=page_size, page=page)
        print("The response of RAGProvidersApi->get_rag_providers_api_v1_tasks_task_id_rag_providers_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGProvidersApi->get_rag_providers_api_v1_tasks_task_id_rag_providers_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**| ID of the task to fetch the provider connections for. | 
 **config_name** | **str**| RAG Provider configuration name substring to search for. | [optional] 
 **authentication_method** | [**RagProviderAuthenticationMethodEnum**](.md)| RAG Provider authentication method to filter by. | [optional] 
 **rag_provider_name** | [**RagAPIKeyAuthenticationProviderEnum**](.md)| RAG provider name to filter by. | [optional] 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**SearchRagProviderConfigurationsResponse**](SearchRagProviderConfigurationsResponse.md)

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

# **list_rag_provider_collections_api_v1_rag_providers_provider_id_collections_get**
> SearchRagProviderCollectionsResponse list_rag_provider_collections_api_v1_rag_providers_provider_id_collections_get(provider_id)

List Rag Provider Collections

Lists all available vector database collections.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.search_rag_provider_collections_response import SearchRagProviderCollectionsResponse
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
    api_instance = arthur_observability_sdk._generated.RAGProvidersApi(api_client)
    provider_id = 'provider_id_example' # str | ID of RAG provider configuration to use for authentication with the vector store.

    try:
        # List Rag Provider Collections
        api_response = api_instance.list_rag_provider_collections_api_v1_rag_providers_provider_id_collections_get(provider_id)
        print("The response of RAGProvidersApi->list_rag_provider_collections_api_v1_rag_providers_provider_id_collections_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGProvidersApi->list_rag_provider_collections_api_v1_rag_providers_provider_id_collections_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **provider_id** | **str**| ID of RAG provider configuration to use for authentication with the vector store. | 

### Return type

[**SearchRagProviderCollectionsResponse**](SearchRagProviderCollectionsResponse.md)

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

# **test_rag_provider_connection_api_v1_tasks_task_id_rag_providers_test_connection_post**
> ConnectionCheckResult test_rag_provider_connection_api_v1_tasks_task_id_rag_providers_test_connection_post(task_id, rag_provider_test_configuration_request)

Test Rag Provider Connection

Test a new RAG provider connection configuration.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.connection_check_result import ConnectionCheckResult
from arthur_observability_sdk._generated.models.rag_provider_test_configuration_request import RagProviderTestConfigurationRequest
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
    api_instance = arthur_observability_sdk._generated.RAGProvidersApi(api_client)
    task_id = 'task_id_example' # str | ID of the task to test the new provider connection for. Should be formatted as a UUID.
    rag_provider_test_configuration_request = arthur_observability_sdk._generated.RagProviderTestConfigurationRequest() # RagProviderTestConfigurationRequest | 

    try:
        # Test Rag Provider Connection
        api_response = api_instance.test_rag_provider_connection_api_v1_tasks_task_id_rag_providers_test_connection_post(task_id, rag_provider_test_configuration_request)
        print("The response of RAGProvidersApi->test_rag_provider_connection_api_v1_tasks_task_id_rag_providers_test_connection_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGProvidersApi->test_rag_provider_connection_api_v1_tasks_task_id_rag_providers_test_connection_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**| ID of the task to test the new provider connection for. Should be formatted as a UUID. | 
 **rag_provider_test_configuration_request** | [**RagProviderTestConfigurationRequest**](RagProviderTestConfigurationRequest.md)|  | 

### Return type

[**ConnectionCheckResult**](ConnectionCheckResult.md)

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

# **update_rag_provider_api_v1_rag_providers_provider_id_patch**
> RagProviderConfigurationResponse update_rag_provider_api_v1_rag_providers_provider_id_patch(provider_id, rag_provider_configuration_update_request)

Update Rag Provider

Update a single RAG provider connection configuration.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.rag_provider_configuration_response import RagProviderConfigurationResponse
from arthur_observability_sdk._generated.models.rag_provider_configuration_update_request import RagProviderConfigurationUpdateRequest
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
    api_instance = arthur_observability_sdk._generated.RAGProvidersApi(api_client)
    provider_id = 'provider_id_example' # str | ID of the RAG provider to update the connection configuration for.
    rag_provider_configuration_update_request = arthur_observability_sdk._generated.RagProviderConfigurationUpdateRequest() # RagProviderConfigurationUpdateRequest | 

    try:
        # Update Rag Provider
        api_response = api_instance.update_rag_provider_api_v1_rag_providers_provider_id_patch(provider_id, rag_provider_configuration_update_request)
        print("The response of RAGProvidersApi->update_rag_provider_api_v1_rag_providers_provider_id_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGProvidersApi->update_rag_provider_api_v1_rag_providers_provider_id_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **provider_id** | **str**| ID of the RAG provider to update the connection configuration for. | 
 **rag_provider_configuration_update_request** | [**RagProviderConfigurationUpdateRequest**](RagProviderConfigurationUpdateRequest.md)|  | 

### Return type

[**RagProviderConfigurationResponse**](RagProviderConfigurationResponse.md)

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

