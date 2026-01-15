# RagNotebookState

Draft state of a RAG notebook - mirrors RAG experiment config but all fields optional. Used for requests (input).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**rag_configs** | [**List[CreateRagExperimentRequestRagConfigsInner]**](CreateRagExperimentRequestRagConfigsInner.md) |  | [optional] 
**dataset_ref** | [**DatasetRefInput**](DatasetRefInput.md) |  | [optional] 
**dataset_row_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**eval_list** | [**List[EvalRefInput]**](EvalRefInput.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.rag_notebook_state import RagNotebookState

# TODO update the JSON string below
json = "{}"
# create an instance of RagNotebookState from a JSON string
rag_notebook_state_instance = RagNotebookState.from_json(json)
# print the JSON string representation of the object
print(RagNotebookState.to_json())

# convert the object into a dict
rag_notebook_state_dict = rag_notebook_state_instance.to_dict()
# create an instance of RagNotebookState from a dict
rag_notebook_state_from_dict = RagNotebookState.from_dict(rag_notebook_state_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


