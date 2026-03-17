# RagNotebookDetail

Detailed RAG notebook information

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | Notebook ID | 
**task_id** | **str** | Associated task ID | 
**name** | **str** | Notebook name | 
**description** | **str** |  | [optional] 
**created_at** | **str** | ISO timestamp when created | 
**updated_at** | **str** | ISO timestamp when last updated | 
**state** | [**RagNotebookStateResponse**](RagNotebookStateResponse.md) | Current draft state | 
**experiments** | [**List[RagExperimentSummary]**](RagExperimentSummary.md) | History of experiments run from this notebook | 

## Example

```python
from arthur_observability_sdk._generated.models.rag_notebook_detail import RagNotebookDetail

# TODO update the JSON string below
json = "{}"
# create an instance of RagNotebookDetail from a JSON string
rag_notebook_detail_instance = RagNotebookDetail.from_json(json)
# print the JSON string representation of the object
print(RagNotebookDetail.to_json())

# convert the object into a dict
rag_notebook_detail_dict = rag_notebook_detail_instance.to_dict()
# create an instance of RagNotebookDetail from a dict
rag_notebook_detail_from_dict = RagNotebookDetail.from_dict(rag_notebook_detail_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


