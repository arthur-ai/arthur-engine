# UserManagementApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**checkUserPermissionUsersPermissionsCheckGet**](#checkuserpermissionuserspermissionscheckget) | **GET** /users/permissions/check | Check User Permission|
|[**createUserUsersPost**](#createuseruserspost) | **POST** /users | Create User|
|[**deleteUserUsersUserIdDelete**](#deleteuserusersuseriddelete) | **DELETE** /users/{user_id} | Delete User|
|[**resetUserPasswordUsersUserIdResetPasswordPost**](#resetuserpasswordusersuseridresetpasswordpost) | **POST** /users/{user_id}/reset_password | Reset User Password|
|[**searchUsersUsersGet**](#searchusersusersget) | **GET** /users | Search Users|

# **checkUserPermissionUsersPermissionsCheckGet**
> any checkUserPermissionUsersPermissionsCheckGet()

Checks if the current user has the requested permission. Returns 200 status code for authorized or 403 if not.

### Example

```typescript
import {
    UserManagementApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new UserManagementApi(configuration);

let action: UserPermissionAction; //Action to check permissions of. (optional) (default to undefined)
let resource: UserPermissionResource; //Resource to check permissions of. (optional) (default to undefined)

const { status, data } = await apiInstance.checkUserPermissionUsersPermissionsCheckGet(
    action,
    resource
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **action** | **UserPermissionAction** | Action to check permissions of. | (optional) defaults to undefined|
| **resource** | **UserPermissionResource** | Resource to check permissions of. | (optional) defaults to undefined|


### Return type

**any**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **createUserUsersPost**
> any createUserUsersPost(createUserRequest)

Creates a new user with specific roles. The available roles are TASK-ADMIN and CHAT-USER. The \'temporary\' field is for indicating if the user password needs to be reset at the first login.

### Example

```typescript
import {
    UserManagementApi,
    Configuration,
    CreateUserRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new UserManagementApi(configuration);

let createUserRequest: CreateUserRequest; //

const { status, data } = await apiInstance.createUserUsersPost(
    createUserRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **createUserRequest** | **CreateUserRequest**|  | |


### Return type

**any**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **deleteUserUsersUserIdDelete**
> any deleteUserUsersUserIdDelete()

Delete a user.

### Example

```typescript
import {
    UserManagementApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new UserManagementApi(configuration);

let userId: string; //User id, not email. (default to undefined)

const { status, data } = await apiInstance.deleteUserUsersUserIdDelete(
    userId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **userId** | [**string**] | User id, not email. | defaults to undefined|


### Return type

**any**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **resetUserPasswordUsersUserIdResetPasswordPost**
> any resetUserPasswordUsersUserIdResetPasswordPost(passwordResetRequest, )

Reset password for user.

### Example

```typescript
import {
    UserManagementApi,
    Configuration,
    PasswordResetRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new UserManagementApi(configuration);

let passwordResetRequest: PasswordResetRequest; //
let userId: string; // (default to undefined)

const { status, data } = await apiInstance.resetUserPasswordUsersUserIdResetPasswordPost(
    passwordResetRequest,
    userId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **passwordResetRequest** | **PasswordResetRequest**|  | |
| **userId** | [**string**] |  | defaults to undefined|


### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **searchUsersUsersGet**
> Array<UserResponse> searchUsersUsersGet()

Fetch users.

### Example

```typescript
import {
    UserManagementApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new UserManagementApi(configuration);

let searchString: string; //Substring to match on. Will search first name, last name, email. (optional) (default to undefined)
let sort: PaginationSortMethod; //Sort the results (asc/desc) (optional) (default to undefined)
let pageSize: number; //Page size. Default is 10. Must be greater than 0 and less than 5000. (optional) (default to 10)
let page: number; //Page number (optional) (default to 0)

const { status, data } = await apiInstance.searchUsersUsersGet(
    searchString,
    sort,
    pageSize,
    page
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **searchString** | [**string**] | Substring to match on. Will search first name, last name, email. | (optional) defaults to undefined|
| **sort** | **PaginationSortMethod** | Sort the results (asc/desc) | (optional) defaults to undefined|
| **pageSize** | [**number**] | Page size. Default is 10. Must be greater than 0 and less than 5000. | (optional) defaults to 10|
| **page** | [**number**] | Page number | (optional) defaults to 0|


### Return type

**Array<UserResponse>**

### Authorization

[API Key](../README.md#API Key)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

