# SearchRagProviderConfigurationsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | The total number of RAG provider configurations matching the parameters. | 
**rag_provider_configurations** | [**List[RagProviderConfigurationResponse]**](RagProviderConfigurationResponse.md) | List of RAG provider configurations matching the search filters. Length is less than or equal to page_size parameter | 

## Example

```python
from arthur_observability_sdk._generated.models.search_rag_provider_configurations_response import SearchRagProviderConfigurationsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SearchRagProviderConfigurationsResponse from a JSON string
search_rag_provider_configurations_response_instance = SearchRagProviderConfigurationsResponse.from_json(json)
# print the JSON string representation of the object
print(SearchRagProviderConfigurationsResponse.to_json())

# convert the object into a dict
search_rag_provider_configurations_response_dict = search_rag_provider_configurations_response_instance.to_dict()
# create an instance of SearchRagProviderConfigurationsResponse from a dict
search_rag_provider_configurations_response_from_dict = SearchRagProviderConfigurationsResponse.from_dict(search_rag_provider_configurations_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


