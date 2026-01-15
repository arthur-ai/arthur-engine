# RagProviderConfigurationResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | Unique identifier of the RAG provider configuration. | 
**task_id** | **str** | ID of parent task. | 
**authentication_config** | [**ApiKeyRagAuthenticationConfigResponse**](ApiKeyRagAuthenticationConfigResponse.md) | Configuration of the authentication strategy. | 
**name** | **str** | Name of RAG provider configuration. | 
**description** | **str** |  | [optional] 
**created_at** | **int** | Time the RAG provider configuration was created in unix milliseconds | 
**updated_at** | **int** | Time the RAG provider configuration was updated in unix milliseconds | 

## Example

```python
from _generated.models.rag_provider_configuration_response import RagProviderConfigurationResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RagProviderConfigurationResponse from a JSON string
rag_provider_configuration_response_instance = RagProviderConfigurationResponse.from_json(json)
# print the JSON string representation of the object
print(RagProviderConfigurationResponse.to_json())

# convert the object into a dict
rag_provider_configuration_response_dict = rag_provider_configuration_response_instance.to_dict()
# create an instance of RagProviderConfigurationResponse from a dict
rag_provider_configuration_response_from_dict = RagProviderConfigurationResponse.from_dict(rag_provider_configuration_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


