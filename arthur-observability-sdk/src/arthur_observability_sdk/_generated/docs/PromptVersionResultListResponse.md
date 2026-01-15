# PromptVersionResultListResponse

Paginated list of results for a specific prompt version

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**page** | **int** | Current page number (0-indexed) | 
**page_size** | **int** | Number of items per page | 
**total_pages** | **int** | Total number of pages | 
**total_count** | **int** | Total number of records | 
**data** | [**List[PromptVersionResult]**](PromptVersionResult.md) | List of results for the prompt version | 

## Example

```python
from arthur_observability_sdk._generated.models.prompt_version_result_list_response import PromptVersionResultListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of PromptVersionResultListResponse from a JSON string
prompt_version_result_list_response_instance = PromptVersionResultListResponse.from_json(json)
# print the JSON string representation of the object
print(PromptVersionResultListResponse.to_json())

# convert the object into a dict
prompt_version_result_list_response_dict = prompt_version_result_list_response_instance.to_dict()
# create an instance of PromptVersionResultListResponse from a dict
prompt_version_result_list_response_from_dict = PromptVersionResultListResponse.from_dict(prompt_version_result_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


