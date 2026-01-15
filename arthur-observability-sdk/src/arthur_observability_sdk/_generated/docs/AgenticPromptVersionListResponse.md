# AgenticPromptVersionListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**versions** | [**List[AgenticPromptVersionResponse]**](AgenticPromptVersionResponse.md) | List of prompt version metadata | 
**count** | **int** | Total number of prompts matching filters | 

## Example

```python
from arthur_observability_sdk._generated.models.agentic_prompt_version_list_response import AgenticPromptVersionListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticPromptVersionListResponse from a JSON string
agentic_prompt_version_list_response_instance = AgenticPromptVersionListResponse.from_json(json)
# print the JSON string representation of the object
print(AgenticPromptVersionListResponse.to_json())

# convert the object into a dict
agentic_prompt_version_list_response_dict = agentic_prompt_version_list_response_instance.to_dict()
# create an instance of AgenticPromptVersionListResponse from a dict
agentic_prompt_version_list_response_from_dict = AgenticPromptVersionListResponse.from_dict(agentic_prompt_version_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


