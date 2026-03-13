# RagNotebookSummary

Summary of a RAG notebook

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | Notebook ID | 
**task_id** | **str** | Associated task ID | 
**name** | **str** | Notebook name | 
**description** | **str** |  | [optional] 
**created_at** | **str** | ISO timestamp when created | 
**updated_at** | **str** | ISO timestamp when last updated | 
**run_count** | **int** | Number of experiments run from this notebook | 
**latest_run_id** | **str** |  | [optional] 
**latest_run_status** | [**ExperimentStatus**](ExperimentStatus.md) |  | [optional] 

## Example

```python
from _generated.models.rag_notebook_summary import RagNotebookSummary

# TODO update the JSON string below
json = "{}"
# create an instance of RagNotebookSummary from a JSON string
rag_notebook_summary_instance = RagNotebookSummary.from_json(json)
# print the JSON string representation of the object
print(RagNotebookSummary.to_json())

# convert the object into a dict
rag_notebook_summary_dict = rag_notebook_summary_instance.to_dict()
# create an instance of RagNotebookSummary from a dict
rag_notebook_summary_from_dict = RagNotebookSummary.from_dict(rag_notebook_summary_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


