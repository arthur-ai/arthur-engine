# ModelProviderModelList


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**provider** | [**ModelProvider**](ModelProvider.md) | Provider of the models | 
**available_models** | **List[str]** | Available models from the provider | 

## Example

```python
from arthur_observability_sdk._generated.models.model_provider_model_list import ModelProviderModelList

# TODO update the JSON string below
json = "{}"
# create an instance of ModelProviderModelList from a JSON string
model_provider_model_list_instance = ModelProviderModelList.from_json(json)
# print the JSON string representation of the object
print(ModelProviderModelList.to_json())

# convert the object into a dict
model_provider_model_list_dict = model_provider_model_list_instance.to_dict()
# create an instance of ModelProviderModelList from a dict
model_provider_model_list_from_dict = ModelProviderModelList.from_dict(model_provider_model_list_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


