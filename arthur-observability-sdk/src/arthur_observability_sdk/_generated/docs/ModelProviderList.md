# ModelProviderList


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**providers** | [**List[ModelProviderResponse]**](ModelProviderResponse.md) | List of model providers | 

## Example

```python
from arthur_observability_sdk._generated.models.model_provider_list import ModelProviderList

# TODO update the JSON string below
json = "{}"
# create an instance of ModelProviderList from a JSON string
model_provider_list_instance = ModelProviderList.from_json(json)
# print the JSON string representation of the object
print(ModelProviderList.to_json())

# convert the object into a dict
model_provider_list_dict = model_provider_list_instance.to_dict()
# create an instance of ModelProviderList from a dict
model_provider_list_from_dict = ModelProviderList.from_dict(model_provider_list_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


