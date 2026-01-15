# RagSearchSettingConfigurationNewVersionRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**settings** | [**Settings**](Settings.md) |  | 
**tags** | **List[str]** | List of tags to configure for this version of the search settings configuration. | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.rag_search_setting_configuration_new_version_request import RagSearchSettingConfigurationNewVersionRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RagSearchSettingConfigurationNewVersionRequest from a JSON string
rag_search_setting_configuration_new_version_request_instance = RagSearchSettingConfigurationNewVersionRequest.from_json(json)
# print the JSON string representation of the object
print(RagSearchSettingConfigurationNewVersionRequest.to_json())

# convert the object into a dict
rag_search_setting_configuration_new_version_request_dict = rag_search_setting_configuration_new_version_request_instance.to_dict()
# create an instance of RagSearchSettingConfigurationNewVersionRequest from a dict
rag_search_setting_configuration_new_version_request_from_dict = RagSearchSettingConfigurationNewVersionRequest.from_dict(rag_search_setting_configuration_new_version_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


