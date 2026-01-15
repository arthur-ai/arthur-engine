# LLMGetAllMetadataResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the llm asset | 
**versions** | **int** | Number of versions of the llm asset | 
**tags** | **List[str]** | List of tags for the llm asset | [optional] 
**created_at** | **datetime** | Timestamp when the llm asset was created | 
**latest_version_created_at** | **datetime** | Timestamp when the last version of the llm asset was created | 
**deleted_versions** | **List[int]** | List of deleted versions of the llm asset | 

## Example

```python
from arthur_observability_sdk._generated.models.llm_get_all_metadata_response import LLMGetAllMetadataResponse

# TODO update the JSON string below
json = "{}"
# create an instance of LLMGetAllMetadataResponse from a JSON string
llm_get_all_metadata_response_instance = LLMGetAllMetadataResponse.from_json(json)
# print the JSON string representation of the object
print(LLMGetAllMetadataResponse.to_json())

# convert the object into a dict
llm_get_all_metadata_response_dict = llm_get_all_metadata_response_instance.to_dict()
# create an instance of LLMGetAllMetadataResponse from a dict
llm_get_all_metadata_response_from_dict = LLMGetAllMetadataResponse.from_dict(llm_get_all_metadata_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


