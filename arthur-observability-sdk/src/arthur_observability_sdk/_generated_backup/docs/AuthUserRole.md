# AuthUserRole


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | [optional] 
**name** | **str** |  | 
**description** | **str** |  | 
**composite** | **bool** |  | 

## Example

```python
from _generated.models.auth_user_role import AuthUserRole

# TODO update the JSON string below
json = "{}"
# create an instance of AuthUserRole from a JSON string
auth_user_role_instance = AuthUserRole.from_json(json)
# print the JSON string representation of the object
print(AuthUserRole.to_json())

# convert the object into a dict
auth_user_role_dict = auth_user_role_instance.to_dict()
# create an instance of AuthUserRole from a dict
auth_user_role_from_dict = AuthUserRole.from_dict(auth_user_role_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


