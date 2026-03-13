# PromptCompletionRequest

Request schema for running an agentic prompt

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variables** | [**List[VariableTemplateValue]**](VariableTemplateValue.md) |  | [optional] 
**strict** | **bool** |  | [optional] 
**stream** | **bool** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.prompt_completion_request import PromptCompletionRequest

# TODO update the JSON string below
json = "{}"
# create an instance of PromptCompletionRequest from a JSON string
prompt_completion_request_instance = PromptCompletionRequest.from_json(json)
# print the JSON string representation of the object
print(PromptCompletionRequest.to_json())

# convert the object into a dict
prompt_completion_request_dict = prompt_completion_request_instance.to_dict()
# create an instance of PromptCompletionRequest from a dict
prompt_completion_request_from_dict = PromptCompletionRequest.from_dict(prompt_completion_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


