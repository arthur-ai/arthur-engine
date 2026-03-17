# ModelProviderResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**provider** | [**ModelProvider**](ModelProvider.md) | The model provider | 
**enabled** | **bool** | Whether the provider is enabled with credentials | 

## Example

```python
from arthur_observability_sdk._generated.models.model_provider_response import ModelProviderResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ModelProviderResponse from a JSON string
model_provider_response_instance = ModelProviderResponse.from_json(json)
# print the JSON string representation of the object
print(ModelProviderResponse.to_json())

# convert the object into a dict
model_provider_response_dict = model_provider_response_instance.to_dict()
# create an instance of ModelProviderResponse from a dict
model_provider_response_from_dict = ModelProviderResponse.from_dict(model_provider_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


