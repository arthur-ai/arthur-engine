# ListRagSearchSettingConfigurationVersionsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | The total number of RAG search setting configuration versions matching the parameters. | 
**rag_provider_setting_configurations** | [**List[RagSearchSettingConfigurationVersionResponse]**](RagSearchSettingConfigurationVersionResponse.md) | List of RAG search setting configuration versions matching the search filters. Length is less than or equal to page_size parameter | 

## Example

```python
from _generated.models.list_rag_search_setting_configuration_versions_response import ListRagSearchSettingConfigurationVersionsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ListRagSearchSettingConfigurationVersionsResponse from a JSON string
list_rag_search_setting_configuration_versions_response_instance = ListRagSearchSettingConfigurationVersionsResponse.from_json(json)
# print the JSON string representation of the object
print(ListRagSearchSettingConfigurationVersionsResponse.to_json())

# convert the object into a dict
list_rag_search_setting_configuration_versions_response_dict = list_rag_search_setting_configuration_versions_response_instance.to_dict()
# create an instance of ListRagSearchSettingConfigurationVersionsResponse from a dict
list_rag_search_setting_configuration_versions_response_from_dict = ListRagSearchSettingConfigurationVersionsResponse.from_dict(list_rag_search_setting_configuration_versions_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


