# RagProviderConfigurationUpdateRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**authentication_config** | [**ApiKeyRagAuthenticationConfigUpdateRequest**](ApiKeyRagAuthenticationConfigUpdateRequest.md) |  | [optional] 
**name** | **str** |  | [optional] 
**description** | **str** |  | [optional] 

## Example

```python
from _generated.models.rag_provider_configuration_update_request import RagProviderConfigurationUpdateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RagProviderConfigurationUpdateRequest from a JSON string
rag_provider_configuration_update_request_instance = RagProviderConfigurationUpdateRequest.from_json(json)
# print the JSON string representation of the object
print(RagProviderConfigurationUpdateRequest.to_json())

# convert the object into a dict
rag_provider_configuration_update_request_dict = rag_provider_configuration_update_request_instance.to_dict()
# create an instance of RagProviderConfigurationUpdateRequest from a dict
rag_provider_configuration_update_request_from_dict = RagProviderConfigurationUpdateRequest.from_dict(rag_provider_configuration_update_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


