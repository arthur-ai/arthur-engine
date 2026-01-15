# RagSearchSettingConfigurationRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**settings** | [**Settings**](Settings.md) |  | 
**rag_provider_id** | **str** | ID of the rag provider to use with the settings. | 
**name** | **str** | Name of the search setting configuration. | 
**description** | **str** |  | [optional] 
**tags** | **List[str]** | List of tags to configure for this version of the search settings configuration. | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.rag_search_setting_configuration_request import RagSearchSettingConfigurationRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RagSearchSettingConfigurationRequest from a JSON string
rag_search_setting_configuration_request_instance = RagSearchSettingConfigurationRequest.from_json(json)
# print the JSON string representation of the object
print(RagSearchSettingConfigurationRequest.to_json())

# convert the object into a dict
rag_search_setting_configuration_request_dict = rag_search_setting_configuration_request_instance.to_dict()
# create an instance of RagSearchSettingConfigurationRequest from a dict
rag_search_setting_configuration_request_from_dict = RagSearchSettingConfigurationRequest.from_dict(rag_search_setting_configuration_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


