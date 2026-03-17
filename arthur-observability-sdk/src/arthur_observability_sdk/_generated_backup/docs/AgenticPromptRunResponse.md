# AgenticPromptRunResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**content** | **str** |  | [optional] 
**tool_calls** | **List[object]** |  | [optional] 
**cost** | **str** |  | 

## Example

```python
from _generated.models.agentic_prompt_run_response import AgenticPromptRunResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticPromptRunResponse from a JSON string
agentic_prompt_run_response_instance = AgenticPromptRunResponse.from_json(json)
# print the JSON string representation of the object
print(AgenticPromptRunResponse.to_json())

# convert the object into a dict
agentic_prompt_run_response_dict = agentic_prompt_run_response_instance.to_dict()
# create an instance of AgenticPromptRunResponse from a dict
agentic_prompt_run_response_from_dict = AgenticPromptRunResponse.from_dict(agentic_prompt_run_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


