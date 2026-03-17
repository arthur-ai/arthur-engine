# RagNotebookStateResponse

Draft state of a RAG notebook - mirrors RAG experiment config but all fields optional. Used for responses (output).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**rag_configs** | [**List[RagExperimentDetailRagConfigsInner]**](RagExperimentDetailRagConfigsInner.md) |  | [optional] 
**dataset_ref** | [**DatasetRef**](DatasetRef.md) |  | [optional] 
**dataset_row_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**eval_list** | [**List[EvalRefOutput]**](EvalRefOutput.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.rag_notebook_state_response import RagNotebookStateResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RagNotebookStateResponse from a JSON string
rag_notebook_state_response_instance = RagNotebookStateResponse.from_json(json)
# print the JSON string representation of the object
print(RagNotebookStateResponse.to_json())

# convert the object into a dict
rag_notebook_state_response_dict = rag_notebook_state_response_instance.to_dict()
# create an instance of RagNotebookStateResponse from a dict
rag_notebook_state_response_from_dict = RagNotebookStateResponse.from_dict(rag_notebook_state_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


