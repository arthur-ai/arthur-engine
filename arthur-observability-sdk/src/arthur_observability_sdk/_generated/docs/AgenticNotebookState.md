# AgenticNotebookState

Draft state of an agentic notebook - mirrors agentic experiment config but all fields optional. Used for requests (input).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**http_template** | [**HttpTemplate**](HttpTemplate.md) |  | [optional] 
**template_variable_mapping** | [**List[TemplateVariableMappingInput]**](TemplateVariableMappingInput.md) |  | [optional] 
**dataset_ref** | [**DatasetRefInput**](DatasetRefInput.md) |  | [optional] 
**dataset_row_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**eval_list** | [**List[AgenticEvalRefInput]**](AgenticEvalRefInput.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.agentic_notebook_state import AgenticNotebookState

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticNotebookState from a JSON string
agentic_notebook_state_instance = AgenticNotebookState.from_json(json)
# print the JSON string representation of the object
print(AgenticNotebookState.to_json())

# convert the object into a dict
agentic_notebook_state_dict = agentic_notebook_state_instance.to_dict()
# create an instance of AgenticNotebookState from a dict
agentic_notebook_state_from_dict = AgenticNotebookState.from_dict(agentic_notebook_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


