# LLMVersionResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **int** | Version number of the llm eval | 
**created_at** | **datetime** | Timestamp when the llm eval version was created | 
**deleted_at** | **datetime** |  | 
**model_provider** | [**ModelProvider**](ModelProvider.md) | Model provider chosen for this version of the llm eval | 
**model_name** | **str** | Model name chosen for this version of the llm eval | 
**tags** | **List[str]** | List of tags for the llm asset | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.llm_version_response import LLMVersionResponse

# TODO update the JSON string below
json = "{}"
# create an instance of LLMVersionResponse from a JSON string
llm_version_response_instance = LLMVersionResponse.from_json(json)
# print the JSON string representation of the object
print(LLMVersionResponse.to_json())

# convert the object into a dict
llm_version_response_dict = llm_version_response_instance.to_dict()
# create an instance of LLMVersionResponse from a dict
llm_version_response_from_dict = LLMVersionResponse.from_dict(llm_version_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


