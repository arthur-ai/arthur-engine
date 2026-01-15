# ListRagSearchSettingConfigurationsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | The total number of RAG search setting configurations matching the parameters. | 
**rag_provider_setting_configurations** | [**List[RagSearchSettingConfigurationResponse]**](RagSearchSettingConfigurationResponse.md) | List of RAG search setting configurations matching the search filters. Length is less than or equal to page_size parameter | 

## Example

```python
from _generated.models.list_rag_search_setting_configurations_response import ListRagSearchSettingConfigurationsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ListRagSearchSettingConfigurationsResponse from a JSON string
list_rag_search_setting_configurations_response_instance = ListRagSearchSettingConfigurationsResponse.from_json(json)
# print the JSON string representation of the object
print(ListRagSearchSettingConfigurationsResponse.to_json())

# convert the object into a dict
list_rag_search_setting_configurations_response_dict = list_rag_search_setting_configurations_response_instance.to_dict()
# create an instance of ListRagSearchSettingConfigurationsResponse from a dict
list_rag_search_setting_configurations_response_from_dict = ListRagSearchSettingConfigurationsResponse.from_dict(list_rag_search_setting_configurations_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


