# RagSearchSettingConfigurationUpdateRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**description** | **str** |  | [optional] 
**rag_provider_id** | **str** |  | [optional] 

## Example

```python
from _generated.models.rag_search_setting_configuration_update_request import RagSearchSettingConfigurationUpdateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RagSearchSettingConfigurationUpdateRequest from a JSON string
rag_search_setting_configuration_update_request_instance = RagSearchSettingConfigurationUpdateRequest.from_json(json)
# print the JSON string representation of the object
print(RagSearchSettingConfigurationUpdateRequest.to_json())

# convert the object into a dict
rag_search_setting_configuration_update_request_dict = rag_search_setting_configuration_update_request_instance.to_dict()
# create an instance of RagSearchSettingConfigurationUpdateRequest from a dict
rag_search_setting_configuration_update_request_from_dict = RagSearchSettingConfigurationUpdateRequest.from_dict(rag_search_setting_configuration_update_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


