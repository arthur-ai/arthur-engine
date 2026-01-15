# _generated.UserManagementApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**check_user_permission_users_permissions_check_get**](UserManagementApi.md#check_user_permission_users_permissions_check_get) | **GET** /users/permissions/check | Check User Permission
[**create_user_users_post**](UserManagementApi.md#create_user_users_post) | **POST** /users | Create User
[**delete_user_users_user_id_delete**](UserManagementApi.md#delete_user_users_user_id_delete) | **DELETE** /users/{user_id} | Delete User
[**reset_user_password_users_user_id_reset_password_post**](UserManagementApi.md#reset_user_password_users_user_id_reset_password_post) | **POST** /users/{user_id}/reset_password | Reset User Password
[**search_users_users_get**](UserManagementApi.md#search_users_users_get) | **GET** /users | Search Users


# **check_user_permission_users_permissions_check_get**
> object check_user_permission_users_permissions_check_get(action=action, resource=resource)

Check User Permission

Checks if the current user has the requested permission. Returns 200 status code for authorized or 403 if not.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.user_permission_action import UserPermissionAction
from _generated.models.user_permission_resource import UserPermissionResource
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
    api_instance = _generated.UserManagementApi(api_client)
    action = _generated.UserPermissionAction() # UserPermissionAction | Action to check permissions of. (optional)
    resource = _generated.UserPermissionResource() # UserPermissionResource | Resource to check permissions of. (optional)

    try:
        # Check User Permission
        api_response = api_instance.check_user_permission_users_permissions_check_get(action=action, resource=resource)
        print("The response of UserManagementApi->check_user_permission_users_permissions_check_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling UserManagementApi->check_user_permission_users_permissions_check_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **action** | [**UserPermissionAction**](.md)| Action to check permissions of. | [optional] 
 **resource** | [**UserPermissionResource**](.md)| Resource to check permissions of. | [optional] 

### Return type

**object**

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

# **create_user_users_post**
> object create_user_users_post(create_user_request)

Create User

Creates a new user with specific roles. The available roles are TASK-ADMIN and CHAT-USER. The 'temporary' field is for indicating if the user password needs to be reset at the first login.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.create_user_request import CreateUserRequest
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
    api_instance = _generated.UserManagementApi(api_client)
    create_user_request = _generated.CreateUserRequest() # CreateUserRequest | 

    try:
        # Create User
        api_response = api_instance.create_user_users_post(create_user_request)
        print("The response of UserManagementApi->create_user_users_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling UserManagementApi->create_user_users_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **create_user_request** | [**CreateUserRequest**](CreateUserRequest.md)|  | 

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
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_user_users_user_id_delete**
> object delete_user_users_user_id_delete(user_id)

Delete User

Delete a user.

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
    api_instance = _generated.UserManagementApi(api_client)
    user_id = 'user_id_example' # str | User id, not email.

    try:
        # Delete User
        api_response = api_instance.delete_user_users_user_id_delete(user_id)
        print("The response of UserManagementApi->delete_user_users_user_id_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling UserManagementApi->delete_user_users_user_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **user_id** | **str**| User id, not email. | 

### Return type

**object**

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

# **reset_user_password_users_user_id_reset_password_post**
> object reset_user_password_users_user_id_reset_password_post(user_id, password_reset_request)

Reset User Password

Reset password for user.

### Example


```python
import _generated
from _generated.models.password_reset_request import PasswordResetRequest
from _generated.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = _generated.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with _generated.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = _generated.UserManagementApi(api_client)
    user_id = 'user_id_example' # str | 
    password_reset_request = _generated.PasswordResetRequest() # PasswordResetRequest | 

    try:
        # Reset User Password
        api_response = api_instance.reset_user_password_users_user_id_reset_password_post(user_id, password_reset_request)
        print("The response of UserManagementApi->reset_user_password_users_user_id_reset_password_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling UserManagementApi->reset_user_password_users_user_id_reset_password_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **user_id** | **str**|  | 
 **password_reset_request** | [**PasswordResetRequest**](PasswordResetRequest.md)|  | 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **search_users_users_get**
> List[UserResponse] search_users_users_get(search_string=search_string, sort=sort, page_size=page_size, page=page)

Search Users

Fetch users.

### Example

* Bearer Authentication (API Key):

```python
import _generated
from _generated.models.pagination_sort_method import PaginationSortMethod
from _generated.models.user_response import UserResponse
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
    api_instance = _generated.UserManagementApi(api_client)
    search_string = 'search_string_example' # str | Substring to match on. Will search first name, last name, email. (optional)
    sort = _generated.PaginationSortMethod() # PaginationSortMethod | Sort the results (asc/desc) (optional)
    page_size = 10 # int | Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
    page = 0 # int | Page number (optional) (default to 0)

    try:
        # Search Users
        api_response = api_instance.search_users_users_get(search_string=search_string, sort=sort, page_size=page_size, page=page)
        print("The response of UserManagementApi->search_users_users_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling UserManagementApi->search_users_users_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **search_string** | **str**| Substring to match on. Will search first name, last name, email. | [optional] 
 **sort** | [**PaginationSortMethod**](.md)| Sort the results (asc/desc) | [optional] 
 **page_size** | **int**| Page size. Default is 10. Must be greater than 0 and less than 5000. | [optional] [default to 10]
 **page** | **int**| Page number | [optional] [default to 0]

### Return type

[**List[UserResponse]**](UserResponse.md)

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

