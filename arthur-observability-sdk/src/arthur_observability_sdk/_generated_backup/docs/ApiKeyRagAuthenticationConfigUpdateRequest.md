# ApiKeyRagAuthenticationConfigUpdateRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**authentication_method** | **str** |  | [optional] [default to 'api_key']
**api_key** | **str** |  | [optional] 
**host_url** | **str** |  | [optional] 
**rag_provider** | [**RagAPIKeyAuthenticationProviderEnum**](RagAPIKeyAuthenticationProviderEnum.md) |  | [optional] 

## Example

```python
from _generated.models.api_key_rag_authentication_config_update_request import ApiKeyRagAuthenticationConfigUpdateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of ApiKeyRagAuthenticationConfigUpdateRequest from a JSON string
api_key_rag_authentication_config_update_request_instance = ApiKeyRagAuthenticationConfigUpdateRequest.from_json(json)
# print the JSON string representation of the object
print(ApiKeyRagAuthenticationConfigUpdateRequest.to_json())

# convert the object into a dict
api_key_rag_authentication_config_update_request_dict = api_key_rag_authentication_config_update_request_instance.to_dict()
# create an instance of ApiKeyRagAuthenticationConfigUpdateRequest from a dict
api_key_rag_authentication_config_update_request_from_dict = ApiKeyRagAuthenticationConfigUpdateRequest.from_dict(api_key_rag_authentication_config_update_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


