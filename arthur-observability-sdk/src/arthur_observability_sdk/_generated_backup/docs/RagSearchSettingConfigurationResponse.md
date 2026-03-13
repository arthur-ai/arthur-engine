# RagSearchSettingConfigurationResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | ID of the setting configuration. | 
**task_id** | **str** | ID of the parent task. | 
**rag_provider_id** | **str** |  | [optional] 
**name** | **str** | Name of the setting configuration. | 
**description** | **str** |  | [optional] 
**latest_version_number** | **int** | The latest version number of the settings configuration. | 
**latest_version** | [**RagSearchSettingConfigurationVersionResponse**](RagSearchSettingConfigurationVersionResponse.md) | The latest version of the settings configuration. | 
**all_possible_tags** | **List[str]** |  | [optional] 
**created_at** | **int** | Time the RAG settings configuration was created in unix milliseconds. | 
**updated_at** | **int** | Time the RAG settings configuration was updated in unix milliseconds. Will be updated if a new version of the configuration was created. | 

## Example

```python
from _generated.models.rag_search_setting_configuration_response import RagSearchSettingConfigurationResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RagSearchSettingConfigurationResponse from a JSON string
rag_search_setting_configuration_response_instance = RagSearchSettingConfigurationResponse.from_json(json)
# print the JSON string representation of the object
print(RagSearchSettingConfigurationResponse.to_json())

# convert the object into a dict
rag_search_setting_configuration_response_dict = rag_search_setting_configuration_response_instance.to_dict()
# create an instance of RagSearchSettingConfigurationResponse from a dict
rag_search_setting_configuration_response_from_dict = RagSearchSettingConfigurationResponse.from_dict(rag_search_setting_configuration_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


