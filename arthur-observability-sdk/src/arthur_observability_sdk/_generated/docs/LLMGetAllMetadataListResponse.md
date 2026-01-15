# LLMGetAllMetadataListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**llm_metadata** | [**List[LLMGetAllMetadataResponse]**](LLMGetAllMetadataResponse.md) | List of llm asset metadata | 
**count** | **int** | Total number of llm assets matching filters | 

## Example

```python
from arthur_observability_sdk._generated.models.llm_get_all_metadata_list_response import LLMGetAllMetadataListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of LLMGetAllMetadataListResponse from a JSON string
llm_get_all_metadata_list_response_instance = LLMGetAllMetadataListResponse.from_json(json)
# print the JSON string representation of the object
print(LLMGetAllMetadataListResponse.to_json())

# convert the object into a dict
llm_get_all_metadata_list_response_dict = llm_get_all_metadata_list_response_instance.to_dict()
# create an instance of LLMGetAllMetadataListResponse from a dict
llm_get_all_metadata_list_response_from_dict = LLMGetAllMetadataListResponse.from_dict(llm_get_all_metadata_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


