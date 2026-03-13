# PutModelProviderCredentials


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**api_key** | **str** | The API key for the provider. | 

## Example

```python
from _generated.models.put_model_provider_credentials import PutModelProviderCredentials

# TODO update the JSON string below
json = "{}"
# create an instance of PutModelProviderCredentials from a JSON string
put_model_provider_credentials_instance = PutModelProviderCredentials.from_json(json)
# print the JSON string representation of the object
print(PutModelProviderCredentials.to_json())

# convert the object into a dict
put_model_provider_credentials_dict = put_model_provider_credentials_instance.to_dict()
# create an instance of PutModelProviderCredentials from a dict
put_model_provider_credentials_from_dict = PutModelProviderCredentials.from_dict(put_model_provider_credentials_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


