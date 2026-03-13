# NotebookStateInput

Draft state of a notebook - mirrors experiment config but all fields optional.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**prompt_configs** | [**List[CreatePromptExperimentRequestPromptConfigsInner]**](CreatePromptExperimentRequestPromptConfigsInner.md) |  | [optional] 
**prompt_variable_mapping** | [**List[PromptVariableMappingInput]**](PromptVariableMappingInput.md) |  | [optional] 
**dataset_ref** | [**DatasetRef**](DatasetRef.md) |  | [optional] 
**dataset_row_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**eval_list** | [**List[EvalRefInput]**](EvalRefInput.md) |  | [optional] 

## Example

```python
from _generated.models.notebook_state_input import NotebookStateInput

# TODO update the JSON string below
json = "{}"
# create an instance of NotebookStateInput from a JSON string
notebook_state_input_instance = NotebookStateInput.from_json(json)
# print the JSON string representation of the object
print(NotebookStateInput.to_json())

# convert the object into a dict
notebook_state_input_dict = notebook_state_input_instance.to_dict()
# create an instance of NotebookStateInput from a dict
notebook_state_input_from_dict = NotebookStateInput.from_dict(notebook_state_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


