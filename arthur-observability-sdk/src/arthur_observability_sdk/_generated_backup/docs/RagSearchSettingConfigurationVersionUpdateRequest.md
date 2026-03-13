# RagSearchSettingConfigurationVersionUpdateRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**tags** | **List[str]** | List of tags to update this version of the search settings configuration with. | 

## Example

```python
from _generated.models.rag_search_setting_configuration_version_update_request import RagSearchSettingConfigurationVersionUpdateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RagSearchSettingConfigurationVersionUpdateRequest from a JSON string
rag_search_setting_configuration_version_update_request_instance = RagSearchSettingConfigurationVersionUpdateRequest.from_json(json)
# print the JSON string representation of the object
print(RagSearchSettingConfigurationVersionUpdateRequest.to_json())

# convert the object into a dict
rag_search_setting_configuration_version_update_request_dict = rag_search_setting_configuration_version_update_request_instance.to_dict()
# create an instance of RagSearchSettingConfigurationVersionUpdateRequest from a dict
rag_search_setting_configuration_version_update_request_from_dict = RagSearchSettingConfigurationVersionUpdateRequest.from_dict(rag_search_setting_configuration_version_update_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


