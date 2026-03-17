# NewApiKeyRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**description** | **str** |  | [optional] 
**roles** | [**List[APIKeysRolesEnum]**](APIKeysRolesEnum.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.new_api_key_request import NewApiKeyRequest

# TODO update the JSON string below
json = "{}"
# create an instance of NewApiKeyRequest from a JSON string
new_api_key_request_instance = NewApiKeyRequest.from_json(json)
# print the JSON string representation of the object
print(NewApiKeyRequest.to_json())

# convert the object into a dict
new_api_key_request_dict = new_api_key_request_instance.to_dict()
# create an instance of NewApiKeyRequest from a dict
new_api_key_request_from_dict = NewApiKeyRequest.from_dict(new_api_key_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


