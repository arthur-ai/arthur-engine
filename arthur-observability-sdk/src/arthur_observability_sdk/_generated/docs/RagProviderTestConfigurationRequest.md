# RagProviderTestConfigurationRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**authentication_config** | [**ApiKeyRagAuthenticationConfigRequest**](ApiKeyRagAuthenticationConfigRequest.md) | Configuration of the authentication strategy. | 

## Example

```python
from arthur_observability_sdk._generated.models.rag_provider_test_configuration_request import RagProviderTestConfigurationRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RagProviderTestConfigurationRequest from a JSON string
rag_provider_test_configuration_request_instance = RagProviderTestConfigurationRequest.from_json(json)
# print the JSON string representation of the object
print(RagProviderTestConfigurationRequest.to_json())

# convert the object into a dict
rag_provider_test_configuration_request_dict = rag_provider_test_configuration_request_instance.to_dict()
# create an instance of RagProviderTestConfigurationRequest from a dict
rag_provider_test_configuration_request_from_dict = RagProviderTestConfigurationRequest.from_dict(rag_provider_test_configuration_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


