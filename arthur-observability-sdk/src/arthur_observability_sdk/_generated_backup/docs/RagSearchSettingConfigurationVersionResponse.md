# RagSearchSettingConfigurationVersionResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**setting_configuration_id** | **str** | ID of the parent setting configuration. | 
**version_number** | **int** | Version number of the setting configuration. | 
**tags** | **List[str]** |  | [optional] 
**settings** | [**Settings1**](Settings1.md) |  | [optional] 
**created_at** | **int** | Time the RAG provider settings configuration version was created in unix milliseconds | 
**updated_at** | **int** | Time the RAG provider settings configuration version was updated in unix milliseconds | 
**deleted_at** | **int** |  | [optional] 

## Example

```python
from _generated.models.rag_search_setting_configuration_version_response import RagSearchSettingConfigurationVersionResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RagSearchSettingConfigurationVersionResponse from a JSON string
rag_search_setting_configuration_version_response_instance = RagSearchSettingConfigurationVersionResponse.from_json(json)
# print the JSON string representation of the object
print(RagSearchSettingConfigurationVersionResponse.to_json())

# convert the object into a dict
rag_search_setting_configuration_version_response_dict = rag_search_setting_configuration_version_response_instance.to_dict()
# create an instance of RagSearchSettingConfigurationVersionResponse from a dict
rag_search_setting_configuration_version_response_from_dict = RagSearchSettingConfigurationVersionResponse.from_dict(rag_search_setting_configuration_version_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


