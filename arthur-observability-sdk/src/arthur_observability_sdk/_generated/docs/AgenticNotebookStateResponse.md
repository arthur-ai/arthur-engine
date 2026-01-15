# AgenticNotebookStateResponse

Draft state of an agentic notebook - mirrors agentic experiment config but all fields optional. Used for responses (output).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**http_template** | [**HttpTemplate**](HttpTemplate.md) |  | [optional] 
**template_variable_mapping** | [**List[TemplateVariableMappingOutput]**](TemplateVariableMappingOutput.md) |  | [optional] 
**dataset_ref** | [**DatasetRef**](DatasetRef.md) |  | [optional] 
**dataset_row_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**eval_list** | [**List[AgenticEvalRefOutput]**](AgenticEvalRefOutput.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.agentic_notebook_state_response import AgenticNotebookStateResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticNotebookStateResponse from a JSON string
agentic_notebook_state_response_instance = AgenticNotebookStateResponse.from_json(json)
# print the JSON string representation of the object
print(AgenticNotebookStateResponse.to_json())

# convert the object into a dict
agentic_notebook_state_response_dict = agentic_notebook_state_response_instance.to_dict()
# create an instance of AgenticNotebookStateResponse from a dict
agentic_notebook_state_response_from_dict = AgenticNotebookStateResponse.from_dict(agentic_notebook_state_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


