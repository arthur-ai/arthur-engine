# ApiKeyRagAuthenticationConfigRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**authentication_method** | **str** |  | [optional] [default to 'api_key']
**api_key** | **str** | API key to use for authentication. | 
**host_url** | **str** | URL of host instance to authenticate with. | 
**rag_provider** | [**RagAPIKeyAuthenticationProviderEnum**](RagAPIKeyAuthenticationProviderEnum.md) | Name of RAG provider to authenticate with. | 

## Example

```python
from arthur_observability_sdk._generated.models.api_key_rag_authentication_config_request import ApiKeyRagAuthenticationConfigRequest

# TODO update the JSON string below
json = "{}"
# create an instance of ApiKeyRagAuthenticationConfigRequest from a JSON string
api_key_rag_authentication_config_request_instance = ApiKeyRagAuthenticationConfigRequest.from_json(json)
# print the JSON string representation of the object
print(ApiKeyRagAuthenticationConfigRequest.to_json())

# convert the object into a dict
api_key_rag_authentication_config_request_dict = api_key_rag_authentication_config_request_instance.to_dict()
# create an instance of ApiKeyRagAuthenticationConfigRequest from a dict
api_key_rag_authentication_config_request_from_dict = ApiKeyRagAuthenticationConfigRequest.from_dict(api_key_rag_authentication_config_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


