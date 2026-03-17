# LLMEvalsVersionListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**versions** | [**List[LLMVersionResponse]**](LLMVersionResponse.md) | List of llm eval version metadata | 
**count** | **int** | Total number of llm evals matching filters | 

## Example

```python
from _generated.models.llm_evals_version_list_response import LLMEvalsVersionListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of LLMEvalsVersionListResponse from a JSON string
llm_evals_version_list_response_instance = LLMEvalsVersionListResponse.from_json(json)
# print the JSON string representation of the object
print(LLMEvalsVersionListResponse.to_json())

# convert the object into a dict
llm_evals_version_list_response_dict = llm_evals_version_list_response_instance.to_dict()
# create an instance of LLMEvalsVersionListResponse from a dict
llm_evals_version_list_response_from_dict = LLMEvalsVersionListResponse.from_dict(llm_evals_version_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


