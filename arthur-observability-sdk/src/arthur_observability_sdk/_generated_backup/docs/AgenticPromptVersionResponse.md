# AgenticPromptVersionResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**version** | **int** | Version number of the llm eval | 
**created_at** | **datetime** | Timestamp when the llm eval version was created | 
**deleted_at** | **datetime** |  | 
**model_provider** | [**ModelProvider**](ModelProvider.md) | Model provider chosen for this version of the llm eval | 
**model_name** | **str** | Model name chosen for this version of the llm eval | 
**tags** | **List[str]** | List of tags for the llm asset | [optional] 
**num_messages** | **int** | Number of messages in the prompt | 
**num_tools** | **int** | Number of tools in the prompt | 

## Example

```python
from _generated.models.agentic_prompt_version_response import AgenticPromptVersionResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticPromptVersionResponse from a JSON string
agentic_prompt_version_response_instance = AgenticPromptVersionResponse.from_json(json)
# print the JSON string representation of the object
print(AgenticPromptVersionResponse.to_json())

# convert the object into a dict
agentic_prompt_version_response_dict = agentic_prompt_version_response_instance.to_dict()
# create an instance of AgenticPromptVersionResponse from a dict
agentic_prompt_version_response_from_dict = AgenticPromptVersionResponse.from_dict(agentic_prompt_version_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


