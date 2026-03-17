# _generated.RAGSettingsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_rag_search_settings**](RAGSettingsApi.md#create_rag_search_settings) | **POST** /api/v1/tasks/{task_id}/rag_search_settings | Create Rag Search Settings
[**create_rag_search_settings_version**](RAGSettingsApi.md#create_rag_search_settings_version) | **POST** /api/v1/rag_search_settings/{setting_configuration_id}/versions | Create Rag Search Settings Version
[**delete_rag_search_setting**](RAGSettingsApi.md#delete_rag_search_setting) | **DELETE** /api/v1/rag_search_settings/{setting_configuration_id} | Delete Rag Search Setting
[**delete_rag_search_setting_version**](RAGSettingsApi.md#delete_rag_search_setting_version) | **DELETE** /api/v1/rag_search_settings/{setting_configuration_id}/versions/{version_number} | Delete Rag Search Setting Version
[**get_rag_search_setting**](RAGSettingsApi.md#get_rag_search_setting) | **GET** /api/v1/rag_search_settings/{setting_configuration_id} | Get Rag Search Setting
[**get_rag_search_setting_configuration_versions_api_v1_rag_search_settings_setting_configuration_id_versions_get**](RAGSettingsApi.md#get_rag_search_setting_configuration_versions_api_v1_rag_search_settings_setting_configuration_id_versions_get) | **GET** /api/v1/rag_search_settings/{setting_configuration_id}/versions | Get Rag Search Setting Configuration Versions
[**get_rag_search_setting_version**](RAGSettingsApi.md#get_rag_search_setting_version) | **GET** /api/v1/rag_search_settings/{setting_configuration_id}/versions/{version_number} | Get Rag Search Setting Version
[**get_rag_search_setting_version_by_tag**](RAGSettingsApi.md#get_rag_search_setting_version_by_tag) | **GET** /api/v1/rag_search_settings/{setting_configuration_id}/versions/tags/{tag} | Get Rag Search Setting Version By Tag
[**get_task_rag_search_settings_api_v1_tasks_task_id_rag_search_settings_get**](RAGSettingsApi.md#get_task_rag_search_settings_api_v1_tasks_task_id_rag_search_settings_get) | **GET** /api/v1/tasks/{task_id}/rag_search_settings | Get Task Rag Search Settings
[**update_rag_search_settings_api_v1_rag_search_settings_setting_configuration_id_patch**](RAGSettingsApi.md#update_rag_search_settings_api_v1_rag_search_settings_setting_configuration_id_patch) | **PATCH** /api/v1/rag_search_settings/{setting_configuration_id} | Update Rag Search Settings
[**update_rag_search_settings_version_api_v1_rag_search_settings_setting_configuration_id_versions_version_number_patch**](RAGSettingsApi.md#update_rag_search_settings_version_api_v1_rag_search_settings_setting_configuration_id_versions_version_number_patch) | **PATCH** /api/v1/rag_search_settings/{setting_configuration_id}/versions/{version_number} | Update Rag Search Settings Version


# **create_rag_search_settings**
> RagSearchSettingConfigurationResponse create_rag_search_settings(task_id, rag_search_setting_configuration_request)

Create Rag Search Settings

Create a new RAG search settings configuration.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.rag_search_setting_configuration_request import RagSearchSettingConfigurationRequest
from _generated.models.rag_search_setting_configuration_response import RagSearchSettingConfigurationResponse
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
    api_instance = _generated.RAGSettingsApi(api_client)
    task_id = 'task_id_example' # str | ID of the task to create the search settings configuration under.
    rag_search_setting_configuration_request = _generated.RagSearchSettingConfigurationRequest() # RagSearchSettingConfigurationRequest | 

    try:
        # Create Rag Search Settings
        api_response = api_instance.create_rag_search_settings(task_id, rag_search_setting_configuration_request)
        print("The response of RAGSettingsApi->create_rag_search_settings:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGSettingsApi->create_rag_search_settings: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**| ID of the task to create the search settings configuration under. | 
 **rag_search_setting_configuration_request** | [**RagSearchSettingConfigurationRequest**](RagSearchSettingConfigurationRequest.md)|  | 

### Return type

[**RagSearchSettingConfigurationResponse**](RagSearchSettingConfigurationResponse.md)

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

# **create_rag_search_settings_version**
> RagSearchSettingConfigurationVersionResponse create_rag_search_settings_version(setting_configuration_id, rag_search_setting_configuration_new_version_request)

Create Rag Search Settings Version

Create a new version for an existing RAG search settings configuration.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.rag_search_setting_configuration_new_version_request import RagSearchSettingConfigurationNewVersionRequest
from _generated.models.rag_search_setting_configuration_version_response import RagSearchSettingConfigurationVersionResponse
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
    api_instance = _generated.RAGSettingsApi(api_client)
    setting_configuration_id = 'setting_configuration_id_example' # str | ID of the RAG settings configuration to create the new version for.
    rag_search_setting_configuration_new_version_request = _generated.RagSearchSettingConfigurationNewVersionRequest() # RagSearchSettingConfigurationNewVersionRequest | 

    try:
        # Create Rag Search Settings Version
        api_response = api_instance.create_rag_search_settings_version(setting_configuration_id, rag_search_setting_configuration_new_version_request)
        print("The response of RAGSettingsApi->create_rag_search_settings_version:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGSettingsApi->create_rag_search_settings_version: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **setting_configuration_id** | **str**| ID of the RAG settings configuration to create the new version for. | 
 **rag_search_setting_configuration_new_version_request** | [**RagSearchSettingConfigurationNewVersionRequest**](RagSearchSettingConfigurationNewVersionRequest.md)|  | 

### Return type

[**RagSearchSettingConfigurationVersionResponse**](RagSearchSettingConfigurationVersionResponse.md)

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

# **delete_rag_search_setting**
> delete_rag_search_setting(setting_configuration_id)

Delete Rag Search Setting

Delete a RAG search setting configuration.

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
    api_instance = _generated.RAGSettingsApi(api_client)
    setting_configuration_id = 'setting_configuration_id_example' # str | ID of RAG setting configuration.

    try:
        # Delete Rag Search Setting
        api_instance.delete_rag_search_setting(setting_configuration_id)
    except Exception as e:
        print("Exception when calling RAGSettingsApi->delete_rag_search_setting: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **setting_configuration_id** | **str**| ID of RAG setting configuration. | 

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

# **delete_rag_search_setting_version**
> delete_rag_search_setting_version(setting_configuration_id, version_number)

Delete Rag Search Setting Version

Soft delete a RAG search setting configuration version.

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
    api_instance = _generated.RAGSettingsApi(api_client)
    setting_configuration_id = 'setting_configuration_id_example' # str | ID of RAG search setting configuration.
    version_number = 56 # int | Version number of the version to delete.

    try:
        # Delete Rag Search Setting Version
        api_instance.delete_rag_search_setting_version(setting_configuration_id, version_number)
    except Exception as e:
        print("Exception when calling RAGSettingsApi->delete_rag_search_setting_version: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **setting_configuration_id** | **str**| ID of RAG search setting configuration. | 
 **version_number** | **int**| Version number of the version to delete. | 

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

# **get_rag_search_setting**
> RagSearchSettingConfigurationResponse get_rag_search_setting(setting_configuration_id)

Get Rag Search Setting

Get a single RAG setting configuration.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.rag_search_setting_configuration_response import RagSearchSettingConfigurationResponse
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
    api_instance = _generated.RAGSettingsApi(api_client)
    setting_configuration_id = 'setting_configuration_id_example' # str | ID of RAG search setting configuration.

    try:
        # Get Rag Search Setting
        api_response = api_instance.get_rag_search_setting(setting_configuration_id)
        print("The response of RAGSettingsApi->get_rag_search_setting:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGSettingsApi->get_rag_search_setting: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **setting_configuration_id** | **str**| ID of RAG search setting configuration. | 

### Return type

[**RagSearchSettingConfigurationResponse**](RagSearchSettingConfigurationResponse.md)

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

# **get_rag_search_setting_configuration_versions_api_v1_rag_search_settings_setting_configuration_id_versions_get**
> ListRagSearchSettingConfigurationVersionsResponse get_rag_search_setting_configuration_versions_api_v1_rag_search_settings_setting_configuration_id_versions_get(setting_configuration_id, tags=tags, version_numbers=version_numbers, sort=sort, page_size=page_size, page=page)

Get Rag Search Setting Configuration Versions

Get list of versions for the RAG search setting configuration.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.list_rag_search_setting_configuration_versions_response import ListRagSearchSettingConfigurationVersionsResponse
from _generated.models.pagination_sort_method import PaginationSortMethod
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
    api_instance = _generated.RAGSettingsApi(api_client)
    setting_configuration_id = 'setting_configuration_id_example' # str | ID of the RAG search setting configuration to get versions for.
    tags = ['tags_example'] # List[str] | List of tags to filter for versions tagged with any matching tag. (optional)
    version_numbers = [56] # List[int] | List of version numbers to filter for. (optional)
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get Rag Search Setting Configuration Versions
        api_response = api_instance.get_rag_search_setting_configuration_versions_api_v1_rag_search_settings_setting_configuration_id_versions_get(setting_configuration_id, tags=tags, version_numbers=version_numbers, sort=sort, page_size=page_size, page=page)
        print("The response of RAGSettingsApi->get_rag_search_setting_configuration_versions_api_v1_rag_search_settings_setting_configuration_id_versions_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGSettingsApi->get_rag_search_setting_configuration_versions_api_v1_rag_search_settings_setting_configuration_id_versions_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **setting_configuration_id** | **str**| ID of the RAG search setting configuration to get versions for. | 
 **tags** | [**List[str]**](str.md)| List of tags to filter for versions tagged with any matching tag. | [optional] 
 **version_numbers** | [**List[int]**](int.md)| List of version numbers to filter for. | [optional] 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**ListRagSearchSettingConfigurationVersionsResponse**](ListRagSearchSettingConfigurationVersionsResponse.md)

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

# **get_rag_search_setting_version**
> RagSearchSettingConfigurationVersionResponse get_rag_search_setting_version(setting_configuration_id, version_number)

Get Rag Search Setting Version

Get a single RAG setting configuration version.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.rag_search_setting_configuration_version_response import RagSearchSettingConfigurationVersionResponse
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
    api_instance = _generated.RAGSettingsApi(api_client)
    setting_configuration_id = 'setting_configuration_id_example' # str | ID of RAG search setting configuration.
    version_number = 56 # int | Version number of the version to fetch.

    try:
        # Get Rag Search Setting Version
        api_response = api_instance.get_rag_search_setting_version(setting_configuration_id, version_number)
        print("The response of RAGSettingsApi->get_rag_search_setting_version:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGSettingsApi->get_rag_search_setting_version: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **setting_configuration_id** | **str**| ID of RAG search setting configuration. | 
 **version_number** | **int**| Version number of the version to fetch. | 

### Return type

[**RagSearchSettingConfigurationVersionResponse**](RagSearchSettingConfigurationVersionResponse.md)

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

# **get_rag_search_setting_version_by_tag**
> RagSearchSettingConfigurationVersionResponse get_rag_search_setting_version_by_tag(setting_configuration_id, tag)

Get Rag Search Setting Version By Tag

Get a single RAG setting configuration version by tag.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.rag_search_setting_configuration_version_response import RagSearchSettingConfigurationVersionResponse
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
    api_instance = _generated.RAGSettingsApi(api_client)
    setting_configuration_id = 'setting_configuration_id_example' # str | ID of RAG search setting configuration.
    tag = 'tag_example' # str | Tag to fetch the version by.

    try:
        # Get Rag Search Setting Version By Tag
        api_response = api_instance.get_rag_search_setting_version_by_tag(setting_configuration_id, tag)
        print("The response of RAGSettingsApi->get_rag_search_setting_version_by_tag:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGSettingsApi->get_rag_search_setting_version_by_tag: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **setting_configuration_id** | **str**| ID of RAG search setting configuration. | 
 **tag** | **str**| Tag to fetch the version by. | 

### Return type

[**RagSearchSettingConfigurationVersionResponse**](RagSearchSettingConfigurationVersionResponse.md)

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

# **get_task_rag_search_settings_api_v1_tasks_task_id_rag_search_settings_get**
> ListRagSearchSettingConfigurationsResponse get_task_rag_search_settings_api_v1_tasks_task_id_rag_search_settings_get(task_id, config_name=config_name, rag_provider_ids=rag_provider_ids, sort=sort, page_size=page_size, page=page)

Get Task Rag Search Settings

Get list of RAG search setting configurations for the task.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.list_rag_search_setting_configurations_response import ListRagSearchSettingConfigurationsResponse
from _generated.models.pagination_sort_method import PaginationSortMethod
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
    api_instance = _generated.RAGSettingsApi(api_client)
    task_id = 'task_id_example' # str | ID of the task to fetch the provider connections for.
    config_name = 'config_name_example' # str | Rag search setting configuration name substring to search for. (optional)
    rag_provider_ids = ['rag_provider_ids_example'] # List[str] | List of rag provider configuration IDs to filter for. (optional)
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get Task Rag Search Settings
        api_response = api_instance.get_task_rag_search_settings_api_v1_tasks_task_id_rag_search_settings_get(task_id, config_name=config_name, rag_provider_ids=rag_provider_ids, sort=sort, page_size=page_size, page=page)
        print("The response of RAGSettingsApi->get_task_rag_search_settings_api_v1_tasks_task_id_rag_search_settings_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGSettingsApi->get_task_rag_search_settings_api_v1_tasks_task_id_rag_search_settings_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**| ID of the task to fetch the provider connections for. | 
 **config_name** | **str**| Rag search setting configuration name substring to search for. | [optional] 
 **rag_provider_ids** | [**List[str]**](str.md)| List of rag provider configuration IDs to filter for. | [optional] 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**ListRagSearchSettingConfigurationsResponse**](ListRagSearchSettingConfigurationsResponse.md)

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

# **update_rag_search_settings_api_v1_rag_search_settings_setting_configuration_id_patch**
> RagSearchSettingConfigurationResponse update_rag_search_settings_api_v1_rag_search_settings_setting_configuration_id_patch(setting_configuration_id, rag_search_setting_configuration_update_request)

Update Rag Search Settings

Update a single RAG search setting configuration.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.rag_search_setting_configuration_response import RagSearchSettingConfigurationResponse
from _generated.models.rag_search_setting_configuration_update_request import RagSearchSettingConfigurationUpdateRequest
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
    api_instance = _generated.RAGSettingsApi(api_client)
    setting_configuration_id = 'setting_configuration_id_example' # str | ID of the RAG setting configuration to update.
    rag_search_setting_configuration_update_request = _generated.RagSearchSettingConfigurationUpdateRequest() # RagSearchSettingConfigurationUpdateRequest | 

    try:
        # Update Rag Search Settings
        api_response = api_instance.update_rag_search_settings_api_v1_rag_search_settings_setting_configuration_id_patch(setting_configuration_id, rag_search_setting_configuration_update_request)
        print("The response of RAGSettingsApi->update_rag_search_settings_api_v1_rag_search_settings_setting_configuration_id_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGSettingsApi->update_rag_search_settings_api_v1_rag_search_settings_setting_configuration_id_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **setting_configuration_id** | **str**| ID of the RAG setting configuration to update. | 
 **rag_search_setting_configuration_update_request** | [**RagSearchSettingConfigurationUpdateRequest**](RagSearchSettingConfigurationUpdateRequest.md)|  | 

### Return type

[**RagSearchSettingConfigurationResponse**](RagSearchSettingConfigurationResponse.md)

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

# **update_rag_search_settings_version_api_v1_rag_search_settings_setting_configuration_id_versions_version_number_patch**
> RagSearchSettingConfigurationVersionResponse update_rag_search_settings_version_api_v1_rag_search_settings_setting_configuration_id_versions_version_number_patch(setting_configuration_id, version_number, rag_search_setting_configuration_version_update_request)

Update Rag Search Settings Version

Update a single RAG search setting configuration version metadata.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.rag_search_setting_configuration_version_response import RagSearchSettingConfigurationVersionResponse
from _generated.models.rag_search_setting_configuration_version_update_request import RagSearchSettingConfigurationVersionUpdateRequest
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
    api_instance = _generated.RAGSettingsApi(api_client)
    setting_configuration_id = 'setting_configuration_id_example' # str | ID of the RAG search setting configuration to update.
    version_number = 56 # int | Version number of the version to update.
    rag_search_setting_configuration_version_update_request = _generated.RagSearchSettingConfigurationVersionUpdateRequest() # RagSearchSettingConfigurationVersionUpdateRequest | 

    try:
        # Update Rag Search Settings Version
        api_response = api_instance.update_rag_search_settings_version_api_v1_rag_search_settings_setting_configuration_id_versions_version_number_patch(setting_configuration_id, version_number, rag_search_setting_configuration_version_update_request)
        print("The response of RAGSettingsApi->update_rag_search_settings_version_api_v1_rag_search_settings_setting_configuration_id_versions_version_number_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RAGSettingsApi->update_rag_search_settings_version_api_v1_rag_search_settings_setting_configuration_id_versions_version_number_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **setting_configuration_id** | **str**| ID of the RAG search setting configuration to update. | 
 **version_number** | **int**| Version number of the version to update. | 
 **rag_search_setting_configuration_version_update_request** | [**RagSearchSettingConfigurationVersionUpdateRequest**](RagSearchSettingConfigurationVersionUpdateRequest.md)|  | 

### Return type

[**RagSearchSettingConfigurationVersionResponse**](RagSearchSettingConfigurationVersionResponse.md)

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

