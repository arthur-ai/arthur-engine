# NotebookStateOutput

Draft state of a notebook - mirrors experiment config but all fields optional.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**prompt_configs** | [**List[CreatePromptExperimentRequestPromptConfigsInner]**](CreatePromptExperimentRequestPromptConfigsInner.md) |  | [optional] 
**prompt_variable_mapping** | [**List[PromptVariableMappingOutput]**](PromptVariableMappingOutput.md) |  | [optional] 
**dataset_ref** | [**DatasetRef**](DatasetRef.md) |  | [optional] 
**dataset_row_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**eval_list** | [**List[EvalRefOutput]**](EvalRefOutput.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.notebook_state_output import NotebookStateOutput

# TODO update the JSON string below
json = "{}"
# create an instance of NotebookStateOutput from a JSON string
notebook_state_output_instance = NotebookStateOutput.from_json(json)
# print the JSON string representation of the object
print(NotebookStateOutput.to_json())

# convert the object into a dict
notebook_state_output_dict = notebook_state_output_instance.to_dict()
# create an instance of NotebookStateOutput from a dict
notebook_state_output_from_dict = NotebookStateOutput.from_dict(notebook_state_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


