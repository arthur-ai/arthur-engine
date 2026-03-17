# _generated.PromptsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put**](PromptsApi.md#add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put) | **PUT** /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/tags | Add a tag to an agentic prompt version
[**delete_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_delete**](PromptsApi.md#delete_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_delete) | **DELETE** /api/v1/tasks/{task_id}/prompts/{prompt_name} | Delete an agentic prompt
[**delete_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_delete**](PromptsApi.md#delete_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_delete) | **DELETE** /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version} | Delete an agentic prompt version
[**delete_tag_from_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_tag_delete**](PromptsApi.md#delete_tag_from_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_tag_delete) | **DELETE** /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/tags/{tag} | Remove a tag from an agentic prompt version
[**get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get**](PromptsApi.md#get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get) | **GET** /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version} | Get an agentic prompt
[**get_agentic_prompt_by_tag_api_v1_tasks_task_id_prompts_prompt_name_versions_tags_tag_get**](PromptsApi.md#get_agentic_prompt_by_tag_api_v1_tasks_task_id_prompts_prompt_name_versions_tags_tag_get) | **GET** /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/tags/{tag} | Get an agentic prompt by name and tag
[**get_all_agentic_prompt_versions_api_v1_tasks_task_id_prompts_prompt_name_versions_get**](PromptsApi.md#get_all_agentic_prompt_versions_api_v1_tasks_task_id_prompts_prompt_name_versions_get) | **GET** /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions | List all versions of an agentic prompt
[**get_all_agentic_prompts_api_v1_tasks_task_id_prompts_get**](PromptsApi.md#get_all_agentic_prompts_api_v1_tasks_task_id_prompts_get) | **GET** /api/v1/tasks/{task_id}/prompts | Get all agentic prompts
[**get_unsaved_prompt_variables_list_api_v1_prompt_variables_post**](PromptsApi.md#get_unsaved_prompt_variables_list_api_v1_prompt_variables_post) | **POST** /api/v1/prompt_variables | Gets the list of variables needed from an unsaved prompt&#39;s messages
[**render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post**](PromptsApi.md#render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post) | **POST** /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/renders | Render a specific version of an agentic prompt with variables
[**render_unsaved_agentic_prompt_api_v1_prompt_renders_post**](PromptsApi.md#render_unsaved_agentic_prompt_api_v1_prompt_renders_post) | **POST** /api/v1/prompt_renders | Render an unsaved prompt with variables
[**run_agentic_prompt_api_v1_completions_post**](PromptsApi.md#run_agentic_prompt_api_v1_completions_post) | **POST** /api/v1/completions | Run/Stream an unsaved agentic prompt
[**run_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_completions_post**](PromptsApi.md#run_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_completions_post) | **POST** /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/completions | Run/Stream a specific version of an agentic prompt
[**save_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_post**](PromptsApi.md#save_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_post) | **POST** /api/v1/tasks/{task_id}/prompts/{prompt_name} | Save an agentic prompt


# **add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put**
> AgenticPrompt add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put(prompt_name, prompt_version, task_id, body_add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put)

Add a tag to an agentic prompt version

Add a tag to an agentic prompt version

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_prompt import AgenticPrompt
from _generated.models.body_add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put import BodyAddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPut
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
    api_instance = _generated.PromptsApi(api_client)
    prompt_name = 'prompt_name_example' # str | The name of the prompt to retrieve.
    prompt_version = 'prompt_version_example' # str | The version of the prompt to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
    task_id = 'task_id_example' # str | 
    body_add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put = _generated.BodyAddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPut() # BodyAddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPut | 

    try:
        # Add a tag to an agentic prompt version
        api_response = api_instance.add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put(prompt_name, prompt_version, task_id, body_add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put)
        print("The response of PromptsApi->add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptsApi->add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **prompt_name** | **str**| The name of the prompt to retrieve. | 
 **prompt_version** | **str**| The version of the prompt to retrieve. Can be &#39;latest&#39;, a version number (e.g. &#39;1&#39;, &#39;2&#39;, etc.), an ISO datetime string (e.g. &#39;2025-01-01T00:00:00&#39;), or a tag. | 
 **task_id** | **str**|  | 
 **body_add_tag_to_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_put** | [**BodyAddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPut**](BodyAddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPut.md)|  | 

### Return type

[**AgenticPrompt**](AgenticPrompt.md)

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

# **delete_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_delete**
> delete_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_delete(prompt_name, task_id)

Delete an agentic prompt

Deletes an entire agentic prompt

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
    api_instance = _generated.PromptsApi(api_client)
    prompt_name = 'prompt_name_example' # str | The name of the prompt to delete.
    task_id = 'task_id_example' # str | 

    try:
        # Delete an agentic prompt
        api_instance.delete_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_delete(prompt_name, task_id)
    except Exception as e:
        print("Exception when calling PromptsApi->delete_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **prompt_name** | **str**| The name of the prompt to delete. | 
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
**204** | Prompt deleted. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_delete**
> delete_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_delete(prompt_name, prompt_version, task_id)

Delete an agentic prompt version

Deletes a specific version of an agentic prompt

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
    api_instance = _generated.PromptsApi(api_client)
    prompt_name = 'prompt_name_example' # str | The name of the prompt to delete.
    prompt_version = 'prompt_version_example' # str | The version of the prompt to delete. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
    task_id = 'task_id_example' # str | 

    try:
        # Delete an agentic prompt version
        api_instance.delete_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_delete(prompt_name, prompt_version, task_id)
    except Exception as e:
        print("Exception when calling PromptsApi->delete_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **prompt_name** | **str**| The name of the prompt to delete. | 
 **prompt_version** | **str**| The version of the prompt to delete. Can be &#39;latest&#39;, a version number (e.g. &#39;1&#39;, &#39;2&#39;, etc.), an ISO datetime string (e.g. &#39;2025-01-01T00:00:00&#39;), or a tag. | 
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
**204** | Prompt version deleted. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_tag_from_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_tag_delete**
> delete_tag_from_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_tag_delete(prompt_name, prompt_version, tag, task_id)

Remove a tag from an agentic prompt version

Remove a tag from an agentic prompt version

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
    api_instance = _generated.PromptsApi(api_client)
    prompt_name = 'prompt_name_example' # str | The name of the prompt to retrieve.
    prompt_version = 'prompt_version_example' # str | The version of the prompt to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
    tag = 'tag_example' # str | The tag to remove from the prompt version.
    task_id = 'task_id_example' # str | 

    try:
        # Remove a tag from an agentic prompt version
        api_instance.delete_tag_from_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_tag_delete(prompt_name, prompt_version, tag, task_id)
    except Exception as e:
        print("Exception when calling PromptsApi->delete_tag_from_agentic_prompt_version_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_tags_tag_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **prompt_name** | **str**| The name of the prompt to retrieve. | 
 **prompt_version** | **str**| The version of the prompt to retrieve. Can be &#39;latest&#39;, a version number (e.g. &#39;1&#39;, &#39;2&#39;, etc.), an ISO datetime string (e.g. &#39;2025-01-01T00:00:00&#39;), or a tag. | 
 **tag** | **str**| The tag to remove from the prompt version. | 
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
**204** | Prompt version deleted. |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get**
> AgenticPrompt get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get(prompt_name, prompt_version, task_id)

Get an agentic prompt

Get an agentic prompt by name and version

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_prompt import AgenticPrompt
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
    api_instance = _generated.PromptsApi(api_client)
    prompt_name = 'prompt_name_example' # str | The name of the prompt to retrieve.
    prompt_version = 'prompt_version_example' # str | The version of the prompt to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
    task_id = 'task_id_example' # str | 

    try:
        # Get an agentic prompt
        api_response = api_instance.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get(prompt_name, prompt_version, task_id)
        print("The response of PromptsApi->get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptsApi->get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **prompt_name** | **str**| The name of the prompt to retrieve. | 
 **prompt_version** | **str**| The version of the prompt to retrieve. Can be &#39;latest&#39;, a version number (e.g. &#39;1&#39;, &#39;2&#39;, etc.), an ISO datetime string (e.g. &#39;2025-01-01T00:00:00&#39;), or a tag. | 
 **task_id** | **str**|  | 

### Return type

[**AgenticPrompt**](AgenticPrompt.md)

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

# **get_agentic_prompt_by_tag_api_v1_tasks_task_id_prompts_prompt_name_versions_tags_tag_get**
> AgenticPrompt get_agentic_prompt_by_tag_api_v1_tasks_task_id_prompts_prompt_name_versions_tags_tag_get(prompt_name, tag, task_id)

Get an agentic prompt by name and tag

Get an agentic prompt by name and tag

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_prompt import AgenticPrompt
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
    api_instance = _generated.PromptsApi(api_client)
    prompt_name = 'prompt_name_example' # str | The name of the prompt to retrieve.
    tag = 'tag_example' # str | The tag of the prompt to retrieve.
    task_id = 'task_id_example' # str | 

    try:
        # Get an agentic prompt by name and tag
        api_response = api_instance.get_agentic_prompt_by_tag_api_v1_tasks_task_id_prompts_prompt_name_versions_tags_tag_get(prompt_name, tag, task_id)
        print("The response of PromptsApi->get_agentic_prompt_by_tag_api_v1_tasks_task_id_prompts_prompt_name_versions_tags_tag_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptsApi->get_agentic_prompt_by_tag_api_v1_tasks_task_id_prompts_prompt_name_versions_tags_tag_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **prompt_name** | **str**| The name of the prompt to retrieve. | 
 **tag** | **str**| The tag of the prompt to retrieve. | 
 **task_id** | **str**|  | 

### Return type

[**AgenticPrompt**](AgenticPrompt.md)

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

# **get_all_agentic_prompt_versions_api_v1_tasks_task_id_prompts_prompt_name_versions_get**
> AgenticPromptVersionListResponse get_all_agentic_prompt_versions_api_v1_tasks_task_id_prompts_prompt_name_versions_get(prompt_name, task_id, sort=sort, page_size=page_size, page=page, model_provider=model_provider, model_name=model_name, created_after=created_after, created_before=created_before, exclude_deleted=exclude_deleted, min_version=min_version, max_version=max_version)

List all versions of an agentic prompt

List all versions of an agentic prompt with optional filtering.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_prompt_version_list_response import AgenticPromptVersionListResponse
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
    api_instance = _generated.PromptsApi(api_client)
    prompt_name = 'prompt_name_example' # str | The name of the prompt to retrieve.
    task_id = 'task_id_example' # str | 
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
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
        # List all versions of an agentic prompt
        api_response = api_instance.get_all_agentic_prompt_versions_api_v1_tasks_task_id_prompts_prompt_name_versions_get(prompt_name, task_id, sort=sort, page_size=page_size, page=page, model_provider=model_provider, model_name=model_name, created_after=created_after, created_before=created_before, exclude_deleted=exclude_deleted, min_version=min_version, max_version=max_version)
        print("The response of PromptsApi->get_all_agentic_prompt_versions_api_v1_tasks_task_id_prompts_prompt_name_versions_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptsApi->get_all_agentic_prompt_versions_api_v1_tasks_task_id_prompts_prompt_name_versions_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **prompt_name** | **str**| The name of the prompt to retrieve. | 
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

[**AgenticPromptVersionListResponse**](AgenticPromptVersionListResponse.md)

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

# **get_all_agentic_prompts_api_v1_tasks_task_id_prompts_get**
> LLMGetAllMetadataListResponse get_all_agentic_prompts_api_v1_tasks_task_id_prompts_get(task_id, sort=sort, page_size=page_size, page=page, llm_asset_names=llm_asset_names, model_provider=model_provider, model_name=model_name, created_after=created_after, created_before=created_before)

Get all agentic prompts

Get all agentic prompts for a given task with optional filtering.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.llm_get_all_metadata_list_response import LLMGetAllMetadataListResponse
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
    api_instance = _generated.PromptsApi(api_client)
    task_id = 'task_id_example' # str | 
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)
    llm_asset_names = ['llm_asset_names_example'] # List[str] | LLM asset names to filter on using partial matching. If provided, llm assets matching any of these name patterns will be returned (optional)
    model_provider = 'model_provider_example' # str | Filter by model provider (e.g., 'openai', 'anthropic', 'azure'). (optional)
    model_name = 'model_name_example' # str | Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet'). (optional)
    created_after = 'created_after_example' # str | Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC). (optional)
    created_before = 'created_before_example' # str | Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC). (optional)

    try:
        # Get all agentic prompts
        api_response = api_instance.get_all_agentic_prompts_api_v1_tasks_task_id_prompts_get(task_id, sort=sort, page_size=page_size, page=page, llm_asset_names=llm_asset_names, model_provider=model_provider, model_name=model_name, created_after=created_after, created_before=created_before)
        print("The response of PromptsApi->get_all_agentic_prompts_api_v1_tasks_task_id_prompts_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptsApi->get_all_agentic_prompts_api_v1_tasks_task_id_prompts_get: %s\n" % e)
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

# **get_unsaved_prompt_variables_list_api_v1_prompt_variables_post**
> UnsavedPromptVariablesListResponse get_unsaved_prompt_variables_list_api_v1_prompt_variables_post(unsaved_prompt_variables_request)

Gets the list of variables needed from an unsaved prompt's messages

Gets the list of variables needed from an unsaved prompt's messages

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.unsaved_prompt_variables_list_response import UnsavedPromptVariablesListResponse
from _generated.models.unsaved_prompt_variables_request import UnsavedPromptVariablesRequest
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
    api_instance = _generated.PromptsApi(api_client)
    unsaved_prompt_variables_request = _generated.UnsavedPromptVariablesRequest() # UnsavedPromptVariablesRequest | 

    try:
        # Gets the list of variables needed from an unsaved prompt's messages
        api_response = api_instance.get_unsaved_prompt_variables_list_api_v1_prompt_variables_post(unsaved_prompt_variables_request)
        print("The response of PromptsApi->get_unsaved_prompt_variables_list_api_v1_prompt_variables_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptsApi->get_unsaved_prompt_variables_list_api_v1_prompt_variables_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **unsaved_prompt_variables_request** | [**UnsavedPromptVariablesRequest**](UnsavedPromptVariablesRequest.md)|  | 

### Return type

[**UnsavedPromptVariablesListResponse**](UnsavedPromptVariablesListResponse.md)

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

# **render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post**
> AgenticPrompt render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post(prompt_name, prompt_version, task_id, saved_prompt_rendering_request=saved_prompt_rendering_request)

Render a specific version of an agentic prompt with variables

Render a specific version of an existing agentic prompt by replacing template variables with provided values. Returns the complete prompt object with rendered messages.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_prompt import AgenticPrompt
from _generated.models.saved_prompt_rendering_request import SavedPromptRenderingRequest
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
    api_instance = _generated.PromptsApi(api_client)
    prompt_name = 'prompt_name_example' # str | The name of the prompt to render.
    prompt_version = 'prompt_version_example' # str | The version of the prompt to render. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
    task_id = 'task_id_example' # str | 
    saved_prompt_rendering_request = _generated.SavedPromptRenderingRequest() # SavedPromptRenderingRequest |  (optional)

    try:
        # Render a specific version of an agentic prompt with variables
        api_response = api_instance.render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post(prompt_name, prompt_version, task_id, saved_prompt_rendering_request=saved_prompt_rendering_request)
        print("The response of PromptsApi->render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptsApi->render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **prompt_name** | **str**| The name of the prompt to render. | 
 **prompt_version** | **str**| The version of the prompt to render. Can be &#39;latest&#39;, a version number (e.g. &#39;1&#39;, &#39;2&#39;, etc.), an ISO datetime string (e.g. &#39;2025-01-01T00:00:00&#39;), or a tag. | 
 **task_id** | **str**|  | 
 **saved_prompt_rendering_request** | [**SavedPromptRenderingRequest**](SavedPromptRenderingRequest.md)|  | [optional] 

### Return type

[**AgenticPrompt**](AgenticPrompt.md)

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

# **render_unsaved_agentic_prompt_api_v1_prompt_renders_post**
> RenderedPromptResponse render_unsaved_agentic_prompt_api_v1_prompt_renders_post(unsaved_prompt_rendering_request)

Render an unsaved prompt with variables

Render an unsaved prompt by replacing template variables with provided values. Accepts messages directly in the request body instead of loading from database.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.rendered_prompt_response import RenderedPromptResponse
from _generated.models.unsaved_prompt_rendering_request import UnsavedPromptRenderingRequest
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
    api_instance = _generated.PromptsApi(api_client)
    unsaved_prompt_rendering_request = _generated.UnsavedPromptRenderingRequest() # UnsavedPromptRenderingRequest | 

    try:
        # Render an unsaved prompt with variables
        api_response = api_instance.render_unsaved_agentic_prompt_api_v1_prompt_renders_post(unsaved_prompt_rendering_request)
        print("The response of PromptsApi->render_unsaved_agentic_prompt_api_v1_prompt_renders_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptsApi->render_unsaved_agentic_prompt_api_v1_prompt_renders_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **unsaved_prompt_rendering_request** | [**UnsavedPromptRenderingRequest**](UnsavedPromptRenderingRequest.md)|  | 

### Return type

[**RenderedPromptResponse**](RenderedPromptResponse.md)

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

# **run_agentic_prompt_api_v1_completions_post**
> AgenticPromptRunResponse run_agentic_prompt_api_v1_completions_post(completion_request)

Run/Stream an unsaved agentic prompt

Runs or streams an unsaved agentic prompt

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_prompt_run_response import AgenticPromptRunResponse
from _generated.models.completion_request import CompletionRequest
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
    api_instance = _generated.PromptsApi(api_client)
    completion_request = _generated.CompletionRequest() # CompletionRequest | 

    try:
        # Run/Stream an unsaved agentic prompt
        api_response = api_instance.run_agentic_prompt_api_v1_completions_post(completion_request)
        print("The response of PromptsApi->run_agentic_prompt_api_v1_completions_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptsApi->run_agentic_prompt_api_v1_completions_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **completion_request** | [**CompletionRequest**](CompletionRequest.md)|  | 

### Return type

[**AgenticPromptRunResponse**](AgenticPromptRunResponse.md)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json, text/event-stream

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | An AgenticPromptRunResponse object for non-streaming requests or a StreamingResponse which has two events, a chunk event or a final_response event |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **run_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_completions_post**
> AgenticPromptRunResponse run_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_completions_post(prompt_name, prompt_version, task_id, prompt_completion_request=prompt_completion_request)

Run/Stream a specific version of an agentic prompt

Run or stream a specific version of an existing agentic prompt

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_prompt_run_response import AgenticPromptRunResponse
from _generated.models.prompt_completion_request import PromptCompletionRequest
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
    api_instance = _generated.PromptsApi(api_client)
    prompt_name = 'prompt_name_example' # str | The name of the prompt to run.
    prompt_version = 'prompt_version_example' # str | The version of the prompt to run. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
    task_id = 'task_id_example' # str | 
    prompt_completion_request = _generated.PromptCompletionRequest() # PromptCompletionRequest |  (optional)

    try:
        # Run/Stream a specific version of an agentic prompt
        api_response = api_instance.run_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_completions_post(prompt_name, prompt_version, task_id, prompt_completion_request=prompt_completion_request)
        print("The response of PromptsApi->run_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_completions_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptsApi->run_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_completions_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **prompt_name** | **str**| The name of the prompt to run. | 
 **prompt_version** | **str**| The version of the prompt to run. Can be &#39;latest&#39;, a version number (e.g. &#39;1&#39;, &#39;2&#39;, etc.), an ISO datetime string (e.g. &#39;2025-01-01T00:00:00&#39;), or a tag. | 
 **task_id** | **str**|  | 
 **prompt_completion_request** | [**PromptCompletionRequest**](PromptCompletionRequest.md)|  | [optional] 

### Return type

[**AgenticPromptRunResponse**](AgenticPromptRunResponse.md)

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json, text/event-stream

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | An AgenticPromptRunResponse object for non-streaming requests or a StreamingResponse which has two events, a chunk event or a final_response event |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **save_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_post**
> AgenticPrompt save_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_post(prompt_name, task_id, create_agentic_prompt_request)

Save an agentic prompt

Save an agentic prompt to the database

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.agentic_prompt import AgenticPrompt
from _generated.models.create_agentic_prompt_request import CreateAgenticPromptRequest
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
    api_instance = _generated.PromptsApi(api_client)
    prompt_name = 'prompt_name_example' # str | The name of the prompt to save.
    task_id = 'task_id_example' # str | 
    create_agentic_prompt_request = _generated.CreateAgenticPromptRequest() # CreateAgenticPromptRequest | 

    try:
        # Save an agentic prompt
        api_response = api_instance.save_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_post(prompt_name, task_id, create_agentic_prompt_request)
        print("The response of PromptsApi->save_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PromptsApi->save_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **prompt_name** | **str**| The name of the prompt to save. | 
 **task_id** | **str**|  | 
 **create_agentic_prompt_request** | [**CreateAgenticPromptRequest**](CreateAgenticPromptRequest.md)|  | 

### Return type

[**AgenticPrompt**](AgenticPrompt.md)

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

