# arthur_observability_sdk._generated.DatasetsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_dataset_api_v2_tasks_task_id_datasets_post**](DatasetsApi.md#create_dataset_api_v2_tasks_task_id_datasets_post) | **POST** /api/v2/tasks/{task_id}/datasets | Create Dataset
[**create_dataset_version_api_v2_datasets_dataset_id_versions_post**](DatasetsApi.md#create_dataset_version_api_v2_datasets_dataset_id_versions_post) | **POST** /api/v2/datasets/{dataset_id}/versions | Create Dataset Version
[**delete_dataset_api_v2_datasets_dataset_id_delete**](DatasetsApi.md#delete_dataset_api_v2_datasets_dataset_id_delete) | **DELETE** /api/v2/datasets/{dataset_id} | Delete Dataset
[**get_dataset_api_v2_datasets_dataset_id_get**](DatasetsApi.md#get_dataset_api_v2_datasets_dataset_id_get) | **GET** /api/v2/datasets/{dataset_id} | Get Dataset
[**get_dataset_version_api_v2_datasets_dataset_id_versions_version_number_get**](DatasetsApi.md#get_dataset_version_api_v2_datasets_dataset_id_versions_version_number_get) | **GET** /api/v2/datasets/{dataset_id}/versions/{version_number} | Get Dataset Version
[**get_dataset_version_row_api_v2_datasets_dataset_id_versions_version_number_rows_row_id_get**](DatasetsApi.md#get_dataset_version_row_api_v2_datasets_dataset_id_versions_version_number_rows_row_id_get) | **GET** /api/v2/datasets/{dataset_id}/versions/{version_number}/rows/{row_id} | Get Dataset Version Row
[**get_dataset_versions_api_v2_datasets_dataset_id_versions_get**](DatasetsApi.md#get_dataset_versions_api_v2_datasets_dataset_id_versions_get) | **GET** /api/v2/datasets/{dataset_id}/versions | Get Dataset Versions
[**get_datasets_api_v2_tasks_task_id_datasets_search_get**](DatasetsApi.md#get_datasets_api_v2_tasks_task_id_datasets_search_get) | **GET** /api/v2/tasks/{task_id}/datasets/search | Get Datasets
[**update_dataset_api_v2_datasets_dataset_id_patch**](DatasetsApi.md#update_dataset_api_v2_datasets_dataset_id_patch) | **PATCH** /api/v2/datasets/{dataset_id} | Update Dataset


# **create_dataset_api_v2_tasks_task_id_datasets_post**
> DatasetResponse create_dataset_api_v2_tasks_task_id_datasets_post(task_id, new_dataset_request)

Create Dataset

Register a new dataset.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.dataset_response import DatasetResponse
from arthur_observability_sdk._generated.models.new_dataset_request import NewDatasetRequest
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
    api_instance = arthur_observability_sdk._generated.DatasetsApi(api_client)
    task_id = 'task_id_example' # str | 
    new_dataset_request = arthur_observability_sdk._generated.NewDatasetRequest() # NewDatasetRequest | 

    try:
        # Create Dataset
        api_response = api_instance.create_dataset_api_v2_tasks_task_id_datasets_post(task_id, new_dataset_request)
        print("The response of DatasetsApi->create_dataset_api_v2_tasks_task_id_datasets_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DatasetsApi->create_dataset_api_v2_tasks_task_id_datasets_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **new_dataset_request** | [**NewDatasetRequest**](NewDatasetRequest.md)|  | 

### Return type

[**DatasetResponse**](DatasetResponse.md)

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

# **create_dataset_version_api_v2_datasets_dataset_id_versions_post**
> DatasetVersionResponse create_dataset_version_api_v2_datasets_dataset_id_versions_post(dataset_id, new_dataset_version_request)

Create Dataset Version

Create a new dataset version.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.dataset_version_response import DatasetVersionResponse
from arthur_observability_sdk._generated.models.new_dataset_version_request import NewDatasetVersionRequest
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
    api_instance = arthur_observability_sdk._generated.DatasetsApi(api_client)
    dataset_id = 'dataset_id_example' # str | ID of the dataset to create a new version for.
    new_dataset_version_request = arthur_observability_sdk._generated.NewDatasetVersionRequest() # NewDatasetVersionRequest | 

    try:
        # Create Dataset Version
        api_response = api_instance.create_dataset_version_api_v2_datasets_dataset_id_versions_post(dataset_id, new_dataset_version_request)
        print("The response of DatasetsApi->create_dataset_version_api_v2_datasets_dataset_id_versions_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DatasetsApi->create_dataset_version_api_v2_datasets_dataset_id_versions_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **dataset_id** | **str**| ID of the dataset to create a new version for. | 
 **new_dataset_version_request** | [**NewDatasetVersionRequest**](NewDatasetVersionRequest.md)|  | 

### Return type

[**DatasetVersionResponse**](DatasetVersionResponse.md)

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

# **delete_dataset_api_v2_datasets_dataset_id_delete**
> delete_dataset_api_v2_datasets_dataset_id_delete(dataset_id)

Delete Dataset

Delete a dataset.

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
    api_instance = arthur_observability_sdk._generated.DatasetsApi(api_client)
    dataset_id = 'dataset_id_example' # str | ID of the dataset to delete.

    try:
        # Delete Dataset
        api_instance.delete_dataset_api_v2_datasets_dataset_id_delete(dataset_id)
    except Exception as e:
        print("Exception when calling DatasetsApi->delete_dataset_api_v2_datasets_dataset_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **dataset_id** | **str**| ID of the dataset to delete. | 

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

# **get_dataset_api_v2_datasets_dataset_id_get**
> DatasetResponse get_dataset_api_v2_datasets_dataset_id_get(dataset_id)

Get Dataset

Get a dataset.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.dataset_response import DatasetResponse
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
    api_instance = arthur_observability_sdk._generated.DatasetsApi(api_client)
    dataset_id = 'dataset_id_example' # str | ID of the dataset to fetch.

    try:
        # Get Dataset
        api_response = api_instance.get_dataset_api_v2_datasets_dataset_id_get(dataset_id)
        print("The response of DatasetsApi->get_dataset_api_v2_datasets_dataset_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DatasetsApi->get_dataset_api_v2_datasets_dataset_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **dataset_id** | **str**| ID of the dataset to fetch. | 

### Return type

[**DatasetResponse**](DatasetResponse.md)

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

# **get_dataset_version_api_v2_datasets_dataset_id_versions_version_number_get**
> DatasetVersionResponse get_dataset_version_api_v2_datasets_dataset_id_versions_version_number_get(dataset_id, version_number, sort=sort, page_size=page_size, page=page)

Get Dataset Version

Fetch a dataset version.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.dataset_version_response import DatasetVersionResponse
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
    api_instance = arthur_observability_sdk._generated.DatasetsApi(api_client)
    dataset_id = 'dataset_id_example' # str | ID of the dataset to fetch the version for.
    version_number = 56 # int | Version number to fetch.
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get Dataset Version
        api_response = api_instance.get_dataset_version_api_v2_datasets_dataset_id_versions_version_number_get(dataset_id, version_number, sort=sort, page_size=page_size, page=page)
        print("The response of DatasetsApi->get_dataset_version_api_v2_datasets_dataset_id_versions_version_number_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DatasetsApi->get_dataset_version_api_v2_datasets_dataset_id_versions_version_number_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **dataset_id** | **str**| ID of the dataset to fetch the version for. | 
 **version_number** | **int**| Version number to fetch. | 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**DatasetVersionResponse**](DatasetVersionResponse.md)

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

# **get_dataset_version_row_api_v2_datasets_dataset_id_versions_version_number_rows_row_id_get**
> DatasetVersionRowResponse get_dataset_version_row_api_v2_datasets_dataset_id_versions_version_number_rows_row_id_get(dataset_id, version_number, row_id)

Get Dataset Version Row

Fetch a specific row from a dataset version by row ID.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.dataset_version_row_response import DatasetVersionRowResponse
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
    api_instance = arthur_observability_sdk._generated.DatasetsApi(api_client)
    dataset_id = 'dataset_id_example' # str | ID of the dataset.
    version_number = 56 # int | Version number of the dataset.
    row_id = 'row_id_example' # str | ID of the row to fetch.

    try:
        # Get Dataset Version Row
        api_response = api_instance.get_dataset_version_row_api_v2_datasets_dataset_id_versions_version_number_rows_row_id_get(dataset_id, version_number, row_id)
        print("The response of DatasetsApi->get_dataset_version_row_api_v2_datasets_dataset_id_versions_version_number_rows_row_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DatasetsApi->get_dataset_version_row_api_v2_datasets_dataset_id_versions_version_number_rows_row_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **dataset_id** | **str**| ID of the dataset. | 
 **version_number** | **int**| Version number of the dataset. | 
 **row_id** | **str**| ID of the row to fetch. | 

### Return type

[**DatasetVersionRowResponse**](DatasetVersionRowResponse.md)

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

# **get_dataset_versions_api_v2_datasets_dataset_id_versions_get**
> ListDatasetVersionsResponse get_dataset_versions_api_v2_datasets_dataset_id_versions_get(dataset_id, latest_version_only=latest_version_only, sort=sort, page_size=page_size, page=page)

Get Dataset Versions

List dataset versions.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.list_dataset_versions_response import ListDatasetVersionsResponse
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
    api_instance = arthur_observability_sdk._generated.DatasetsApi(api_client)
    dataset_id = 'dataset_id_example' # str | ID of the dataset to fetch versions for.
    latest_version_only = False # bool | Whether to only include the latest version for the dataset in the response. Defaults to False. (optional) (default to False)
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get Dataset Versions
        api_response = api_instance.get_dataset_versions_api_v2_datasets_dataset_id_versions_get(dataset_id, latest_version_only=latest_version_only, sort=sort, page_size=page_size, page=page)
        print("The response of DatasetsApi->get_dataset_versions_api_v2_datasets_dataset_id_versions_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DatasetsApi->get_dataset_versions_api_v2_datasets_dataset_id_versions_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **dataset_id** | **str**| ID of the dataset to fetch versions for. | 
 **latest_version_only** | **bool**| Whether to only include the latest version for the dataset in the response. Defaults to False. | [optional] [default to False]
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**ListDatasetVersionsResponse**](ListDatasetVersionsResponse.md)

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

# **get_datasets_api_v2_tasks_task_id_datasets_search_get**
> SearchDatasetsResponse get_datasets_api_v2_tasks_task_id_datasets_search_get(task_id, dataset_ids=dataset_ids, dataset_name=dataset_name, sort=sort, page_size=page_size, page=page)

Get Datasets

Search datasets. Optionally can filter by dataset IDs and dataset name.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.pagination_sort_method import PaginationSortMethod
from arthur_observability_sdk._generated.models.search_datasets_response import SearchDatasetsResponse
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
    api_instance = arthur_observability_sdk._generated.DatasetsApi(api_client)
    task_id = 'task_id_example' # str | 
    dataset_ids = ['dataset_ids_example'] # List[str] | List of dataset ids to query for. (optional)
    dataset_name = 'dataset_name_example' # str | Dataset name substring to search for. (optional)
    sort = arthur_observability_sdk._generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Get Datasets
        api_response = api_instance.get_datasets_api_v2_tasks_task_id_datasets_search_get(task_id, dataset_ids=dataset_ids, dataset_name=dataset_name, sort=sort, page_size=page_size, page=page)
        print("The response of DatasetsApi->get_datasets_api_v2_tasks_task_id_datasets_search_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DatasetsApi->get_datasets_api_v2_tasks_task_id_datasets_search_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **task_id** | **str**|  | 
 **dataset_ids** | [**List[str]**](str.md)| List of dataset ids to query for. | [optional] 
 **dataset_name** | **str**| Dataset name substring to search for. | [optional] 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**SearchDatasetsResponse**](SearchDatasetsResponse.md)

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

# **update_dataset_api_v2_datasets_dataset_id_patch**
> DatasetResponse update_dataset_api_v2_datasets_dataset_id_patch(dataset_id, dataset_update_request)

Update Dataset

Update a dataset.

### Example

* Bearer Authentication (API Key):

```python
import arthur_observability_sdk._generated
from arthur_observability_sdk._generated.models.dataset_response import DatasetResponse
from arthur_observability_sdk._generated.models.dataset_update_request import DatasetUpdateRequest
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
    api_instance = arthur_observability_sdk._generated.DatasetsApi(api_client)
    dataset_id = 'dataset_id_example' # str | ID of the dataset to update.
    dataset_update_request = arthur_observability_sdk._generated.DatasetUpdateRequest() # DatasetUpdateRequest | 

    try:
        # Update Dataset
        api_response = api_instance.update_dataset_api_v2_datasets_dataset_id_patch(dataset_id, dataset_update_request)
        print("The response of DatasetsApi->update_dataset_api_v2_datasets_dataset_id_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DatasetsApi->update_dataset_api_v2_datasets_dataset_id_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **dataset_id** | **str**| ID of the dataset to update. | 
 **dataset_update_request** | [**DatasetUpdateRequest**](DatasetUpdateRequest.md)|  | 

### Return type

[**DatasetResponse**](DatasetResponse.md)

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

