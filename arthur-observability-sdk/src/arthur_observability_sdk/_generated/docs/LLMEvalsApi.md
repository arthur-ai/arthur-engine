# arthur_observability_sdk._generated.LLMEvalsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put**](LLMEvalsApi.md#add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put) | **PUT** /api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/tags | Add a tag to an llm eval version
[**delete_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_delete**](LLMEvalsApi.md#delete_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_delete) | **DELETE** /api/v1/tasks/{task_id}/llm_evals/{eval_name} | Delete an llm eval
[**delete_tag_from_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_tag_delete**](LLMEvalsApi.md#delete_tag_from_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_tag_delete) | **DELETE** /api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/tags/{tag} | Remove a tag from an llm eval version
[**get_all_llm_eval_versions_api_v1_tasks_task_id_llm_evals_eval_name_versions_get**](LLMEvalsApi.md#get_all_llm_eval_versions_api_v1_tasks_task_id_llm_evals_eval_name_versions_get) | **GET** /api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions | List all versions of an llm eval
[**get_all_llm_evals_api_v1_tasks_task_id_llm_evals_get**](LLMEvalsApi.md#get_all_llm_evals_api_v1_tasks_task_id_llm_evals_get) | **GET** /api/v1/tasks/{task_id}/llm_evals | Get all llm evals
[**get_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_get**](LLMEvalsApi.md#get_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_get) | **GET** /api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version} | Get an llm eval
[**get_llm_eval_by_tag_api_v1_tasks_task_id_llm_evals_eval_name_versions_tags_tag_get**](LLMEvalsApi.md#get_llm_eval_by_tag_api_v1_tasks_task_id_llm_evals_eval_name_versions_tags_tag_get) | **GET** /api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/tags/{tag} | Get an llm eval by name and tag
[**run_saved_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_completions_post**](LLMEvalsApi.md#run_saved_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_completions_post) | **POST** /api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/completions | Run a saved llm eval
[**save_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_post**](LLMEvalsApi.md#save_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_post) | **POST** /api/v1/tasks/{task_id}/llm_evals/{eval_name} | Save an llm eval
[**soft_delete_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_delete**](LLMEvalsApi.md#soft_delete_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_delete) | **DELETE** /api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version} | Delete an llm eval version


# **add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put**
> LLMEval add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put(eval_name, eval_version, task_id, body_add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put)

Add a tag to an llm eval version

Add a tag to an llm eval version

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.body_add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put import BodyAddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPut
from arthur_observability_sdk._generated.models.llm_eval import LLMEval
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
    api_instance = arthur_observability_sdk._generated.LLMEvalsApi(api_client)
    eval_name = 'eval_name_example' # str | The name of the llm eval to retrieve.
    eval_version = 'eval_version_example' # str | The version of the llm eval to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
    task_id = 'task_id_example' # str | 
    body_add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put = arthur_observability_sdk._generated.BodyAddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPut() # BodyAddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPut | 

    try:
        # Add a tag to an llm eval version
        api_response = api_instance.add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put(eval_name, eval_version, task_id, body_add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put)
        print("The response of LLMEvalsApi->add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling LLMEvalsApi->add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **eval_name** | **str**| The name of the llm eval to retrieve. | 
 **eval_version** | **str**| The version of the llm eval to retrieve. Can be &#39;latest&#39;, a version number (e.g. &#39;1&#39;, &#39;2&#39;, etc.), an ISO datetime string (e.g. &#39;2025-01-01T00:00:00&#39;), or a tag. | 
 **task_id** | **str**|  | 
 **body_add_tag_to_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_put** | [**BodyAddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPut**](BodyAddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPut.md)|  | 

### Return type

[**LLMEval**](LLMEval.md)

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

# **delete_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_delete**
> delete_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_delete(eval_name, task_id)

Delete an llm eval

Deletes an entire llm eval

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
    api_instance = arthur_observability_sdk._generated.LLMEvalsApi(api_client)
    eval_name = 'eval_name_example' # str | The name of the llm eval to delete.
    task_id = 'task_id_example' # str | 

    try:
        # Delete an llm eval
        api_instance.delete_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_delete(eval_name, task_id)
    except Exception as e:
        print("Exception when calling LLMEvalsApi->delete_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **eval_name** | **str**| The name of the llm eval to delete. | 
 **task_id** | **str**|  | 

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
**204** | LLM eval deleted. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_tag_from_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_tag_delete**
> delete_tag_from_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_tag_delete(eval_name, eval_version, tag, task_id)

Remove a tag from an llm eval version

Remove a tag from an llm eval version

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
    api_instance = arthur_observability_sdk._generated.LLMEvalsApi(api_client)
    eval_name = 'eval_name_example' # str | The name of the llm eval to retrieve.
    eval_version = 'eval_version_example' # str | The version of the llm eval to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
    tag = 'tag_example' # str | The tag to remove from the llm eval version.
    task_id = 'task_id_example' # str | 

    try:
        # Remove a tag from an llm eval version
        api_instance.delete_tag_from_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_tag_delete(eval_name, eval_version, tag, task_id)
    except Exception as e:
        print("Exception when calling LLMEvalsApi->delete_tag_from_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_tags_tag_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **eval_name** | **str**| The name of the llm eval to retrieve. | 
 **eval_version** | **str**| The version of the llm eval to retrieve. Can be &#39;latest&#39;, a version number (e.g. &#39;1&#39;, &#39;2&#39;, etc.), an ISO datetime string (e.g. &#39;2025-01-01T00:00:00&#39;), or a tag. | 
 **tag** | **str**| The tag to remove from the llm eval version. | 
 **task_id** | **str**|  | 

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
**204** | LLM eval version deleted. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_all_llm_eval_versions_api_v1_tasks_task_id_llm_evals_eval_name_versions_get**
> LLMEvalsVersionListResponse get_all_llm_eval_versions_api_v1_tasks_task_id_llm_evals_eval_name_versions_get(eval_name, task_id, sort=sort, page_size=page_size, page=page, model_provider=model_provider, model_name=model_name, created_after=created_after, created_before=created_before, exclude_deleted=exclude_deleted, min_version=min_version, max_version=max_version)

List all versions of an llm eval

List all versions of an llm eval with optional filtering.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.llm_evals_version_list_response import LLMEvalsVersionListResponse
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
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
    api_instance = arthur_observability_sdk._generated.LLMEvalsApi(api_client)
    eval_name = 'eval_name_example' # str | The name of the llm eval to retrieve.
    task_id = 'task_id_example' # str | 
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)
    model_provider = 'model_provider_example' # str | Filter by model provider (e.g., 'openai', 'anthropic', 'azure'). (optional)
    model_name = 'model_name_example' # str | Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet'). (optional)
    created_after = 'created_after_example' # str | Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC). (optional)
    created_before = 'created_before_example' # str | Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC). (optional)
    exclude_deleted = False # bool | Whether to exclude deleted prompt versions from the results. Default is False. (optional) (default to False)
    min_version = 56 # int | Minimum version number to filter on (inclusive). (optional)
    max_version = 56 # int | Maximum version number to filter on (inclusive). (optional)

    try:
        # List all versions of an llm eval
        api_response = api_instance.get_all_llm_eval_versions_api_v1_tasks_task_id_llm_evals_eval_name_versions_get(eval_name, task_id, sort=sort, page_size=page_size, page=page, model_provider=model_provider, model_name=model_name, created_after=created_after, created_before=created_before, exclude_deleted=exclude_deleted, min_version=min_version, max_version=max_version)
        print("The response of LLMEvalsApi->get_all_llm_eval_versions_api_v1_tasks_task_id_llm_evals_eval_name_versions_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling LLMEvalsApi->get_all_llm_eval_versions_api_v1_tasks_task_id_llm_evals_eval_name_versions_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **eval_name** | **str**| The name of the llm eval to retrieve. | 
 **task_id** | **str**|  | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]
 **model_provider** | **str**| Filter by model provider (e.g., &#39;openai&#39;, &#39;anthropic&#39;, &#39;azure&#39;). | [optional] 
 **model_name** | **str**| Filter by model name (e.g., &#39;gpt-4&#39;, &#39;claude-3-5-sonnet&#39;). | [optional] 
 **created_after** | **str**| Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC). | [optional] 
 **created_before** | **str**| Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC). | [optional] 
 **exclude_deleted** | **bool**| Whether to exclude deleted prompt versions from the results. Default is False. | [optional] [default to False]
 **min_version** | **int**| Minimum version number to filter on (inclusive). | [optional] 
 **max_version** | **int**| Maximum version number to filter on (inclusive). | [optional] 

### Return type

[**LLMEvalsVersionListResponse**](LLMEvalsVersionListResponse.md)

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

# **get_all_llm_evals_api_v1_tasks_task_id_llm_evals_get**
> LLMGetAllMetadataListResponse get_all_llm_evals_api_v1_tasks_task_id_llm_evals_get(task_id, sort=sort, page_size=page_size, page=page, llm_asset_names=llm_asset_names, model_provider=model_provider, model_name=model_name, created_after=created_after, created_before=created_before)

Get all llm evals

Get all llm evals for a given task with optional filtering.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.llm_get_all_metadata_list_response import LLMGetAllMetadataListResponse
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
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
    api_instance = arthur_observability_sdk._generated.LLMEvalsApi(api_client)
    task_id = 'task_id_example' # str | 
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)
    llm_asset_names = ['llm_asset_names_example'] # List[str] | LLM asset names to filter on using partial matching. If provided, llm assets matching any of these name patterns will be returned (optional)
    model_provider = 'model_provider_example' # str | Filter by model provider (e.g., 'openai', 'anthropic', 'azure'). (optional)
    model_name = 'model_name_example' # str | Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet'). (optional)
    created_after = 'created_after_example' # str | Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC). (optional)
    created_before = 'created_before_example' # str | Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC). (optional)

    try:
        # Get all llm evals
        api_response = api_instance.get_all_llm_evals_api_v1_tasks_task_id_llm_evals_get(task_id, sort=sort, page_size=page_size, page=page, llm_asset_names=llm_asset_names, model_provider=model_provider, model_name=model_name, created_after=created_after, created_before=created_before)
        print("The response of LLMEvalsApi->get_all_llm_evals_api_v1_tasks_task_id_llm_evals_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling LLMEvalsApi->get_all_llm_evals_api_v1_tasks_task_id_llm_evals_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]
 **llm_asset_names** | [**List[str]**](str.md)| LLM asset names to filter on using partial matching. If provided, llm assets matching any of these name patterns will be returned | [optional] 
 **model_provider** | **str**| Filter by model provider (e.g., &#39;openai&#39;, &#39;anthropic&#39;, &#39;azure&#39;). | [optional] 
 **model_name** | **str**| Filter by model name (e.g., &#39;gpt-4&#39;, &#39;claude-3-5-sonnet&#39;). | [optional] 
 **created_after** | **str**| Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC). | [optional] 
 **created_before** | **str**| Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC). | [optional] 

### Return type

[**LLMGetAllMetadataListResponse**](LLMGetAllMetadataListResponse.md)

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

# **get_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_get**
> LLMEval get_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_get(eval_name, eval_version, task_id)

Get an llm eval

Get an llm eval by name and version

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.llm_eval import LLMEval
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
    api_instance = arthur_observability_sdk._generated.LLMEvalsApi(api_client)
    eval_name = 'eval_name_example' # str | The name of the llm eval to retrieve.
    eval_version = 'eval_version_example' # str | The version of the llm eval to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
    task_id = 'task_id_example' # str | 

    try:
        # Get an llm eval
        api_response = api_instance.get_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_get(eval_name, eval_version, task_id)
        print("The response of LLMEvalsApi->get_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling LLMEvalsApi->get_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **eval_name** | **str**| The name of the llm eval to retrieve. | 
 **eval_version** | **str**| The version of the llm eval to retrieve. Can be &#39;latest&#39;, a version number (e.g. &#39;1&#39;, &#39;2&#39;, etc.), an ISO datetime string (e.g. &#39;2025-01-01T00:00:00&#39;), or a tag. | 
 **task_id** | **str**|  | 

### Return type

[**LLMEval**](LLMEval.md)

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

# **get_llm_eval_by_tag_api_v1_tasks_task_id_llm_evals_eval_name_versions_tags_tag_get**
> LLMEval get_llm_eval_by_tag_api_v1_tasks_task_id_llm_evals_eval_name_versions_tags_tag_get(eval_name, tag, task_id)

Get an llm eval by name and tag

Get an llm eval by name and tag

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.llm_eval import LLMEval
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
    api_instance = arthur_observability_sdk._generated.LLMEvalsApi(api_client)
    eval_name = 'eval_name_example' # str | The name of the llm eval to retrieve.
    tag = 'tag_example' # str | The tag of the llm eval to retrieve.
    task_id = 'task_id_example' # str | 

    try:
        # Get an llm eval by name and tag
        api_response = api_instance.get_llm_eval_by_tag_api_v1_tasks_task_id_llm_evals_eval_name_versions_tags_tag_get(eval_name, tag, task_id)
        print("The response of LLMEvalsApi->get_llm_eval_by_tag_api_v1_tasks_task_id_llm_evals_eval_name_versions_tags_tag_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling LLMEvalsApi->get_llm_eval_by_tag_api_v1_tasks_task_id_llm_evals_eval_name_versions_tags_tag_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **eval_name** | **str**| The name of the llm eval to retrieve. | 
 **tag** | **str**| The tag of the llm eval to retrieve. | 
 **task_id** | **str**|  | 

### Return type

[**LLMEval**](LLMEval.md)

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

# **run_saved_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_completions_post**
> LLMEvalRunResponse run_saved_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_completions_post(eval_name, eval_version, task_id, base_completion_request)

Run a saved llm eval

Run a saved llm eval

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.base_completion_request import BaseCompletionRequest
from arthur_observability_sdk._generated.models.llm_eval_run_response import LLMEvalRunResponse
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
    api_instance = arthur_observability_sdk._generated.LLMEvalsApi(api_client)
    eval_name = 'eval_name_example' # str | The name of the llm eval to run.
    eval_version = 'eval_version_example' # str | The version of the llm eval to run. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
    task_id = 'task_id_example' # str | 
    base_completion_request = arthur_observability_sdk._generated.BaseCompletionRequest() # BaseCompletionRequest | 

    try:
        # Run a saved llm eval
        api_response = api_instance.run_saved_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_completions_post(eval_name, eval_version, task_id, base_completion_request)
        print("The response of LLMEvalsApi->run_saved_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_completions_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling LLMEvalsApi->run_saved_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_completions_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **eval_name** | **str**| The name of the llm eval to run. | 
 **eval_version** | **str**| The version of the llm eval to run. Can be &#39;latest&#39;, a version number (e.g. &#39;1&#39;, &#39;2&#39;, etc.), an ISO datetime string (e.g. &#39;2025-01-01T00:00:00&#39;), or a tag. | 
 **task_id** | **str**|  | 
 **base_completion_request** | [**BaseCompletionRequest**](BaseCompletionRequest.md)|  | 

### Return type

[**LLMEvalRunResponse**](LLMEvalRunResponse.md)

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

# **save_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_post**
> LLMEval save_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_post(eval_name, task_id, create_eval_request)

Save an llm eval

Save an llm eval to the database

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.create_eval_request import CreateEvalRequest
from arthur_observability_sdk._generated.models.llm_eval import LLMEval
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
    api_instance = arthur_observability_sdk._generated.LLMEvalsApi(api_client)
    eval_name = 'eval_name_example' # str | The name of the llm eval to save.
    task_id = 'task_id_example' # str | 
    create_eval_request = arthur_observability_sdk._generated.CreateEvalRequest() # CreateEvalRequest | 

    try:
        # Save an llm eval
        api_response = api_instance.save_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_post(eval_name, task_id, create_eval_request)
        print("The response of LLMEvalsApi->save_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling LLMEvalsApi->save_llm_eval_api_v1_tasks_task_id_llm_evals_eval_name_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **eval_name** | **str**| The name of the llm eval to save. | 
 **task_id** | **str**|  | 
 **create_eval_request** | [**CreateEvalRequest**](CreateEvalRequest.md)|  | 

### Return type

[**LLMEval**](LLMEval.md)

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

# **soft_delete_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_delete**
> soft_delete_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_delete(eval_name, eval_version, task_id)

Delete an llm eval version

Deletes a specific version of an llm eval

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
    api_instance = arthur_observability_sdk._generated.LLMEvalsApi(api_client)
    eval_name = 'eval_name_example' # str | The name of the llm eval to delete.
    eval_version = 'eval_version_example' # str | The version of the llm eval to delete. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
    task_id = 'task_id_example' # str | 

    try:
        # Delete an llm eval version
        api_instance.soft_delete_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_delete(eval_name, eval_version, task_id)
    except Exception as e:
        print("Exception when calling LLMEvalsApi->soft_delete_llm_eval_version_api_v1_tasks_task_id_llm_evals_eval_name_versions_eval_version_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **eval_name** | **str**| The name of the llm eval to delete. | 
 **eval_version** | **str**| The version of the llm eval to delete. Can be &#39;latest&#39;, a version number (e.g. &#39;1&#39;, &#39;2&#39;, etc.), an ISO datetime string (e.g. &#39;2025-01-01T00:00:00&#39;), or a tag. | 
 **task_id** | **str**|  | 

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
**204** | LLM eval version deleted. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

