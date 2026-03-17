# ApiKeyRagAuthenticationConfigResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**authentication_method** | **str** |  | [optional] [default to 'api_key']
**host_url** | **str** | URL of host instance to authenticate with. | 
**rag_provider** | [**RagAPIKeyAuthenticationProviderEnum**](RagAPIKeyAuthenticationProviderEnum.md) | Name of RAG provider to authenticate with. | 

## Example

```python
from _generated.models.api_key_rag_authentication_config_response import ApiKeyRagAuthenticationConfigResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ApiKeyRagAuthenticationConfigResponse from a JSON string
api_key_rag_authentication_config_response_instance = ApiKeyRagAuthenticationConfigResponse.from_json(json)
# print the JSON string representation of the object
print(ApiKeyRagAuthenticationConfigResponse.to_json())

# convert the object into a dict
api_key_rag_authentication_config_response_dict = api_key_rag_authentication_config_response_instance.to_dict()
# create an instance of ApiKeyRagAuthenticationConfigResponse from a dict
api_key_rag_authentication_config_response_from_dict = ApiKeyRagAuthenticationConfigResponse.from_dict(api_key_rag_authentication_config_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


