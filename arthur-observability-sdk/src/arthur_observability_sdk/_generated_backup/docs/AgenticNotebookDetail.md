# AgenticNotebookDetail

Detailed agentic notebook information

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | Notebook ID | 
**task_id** | **str** | Associated task ID | 
**name** | **str** | Notebook name | 
**description** | **str** |  | [optional] 
**created_at** | **str** | ISO timestamp when created | 
**updated_at** | **str** | ISO timestamp when last updated | 
**state** | [**AgenticNotebookStateResponse**](AgenticNotebookStateResponse.md) | Current draft state | 
**experiments** | [**List[AgenticExperimentSummary]**](AgenticExperimentSummary.md) | History of experiments run from this notebook | 

## Example

```python
from _generated.models.agentic_notebook_detail import AgenticNotebookDetail

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticNotebookDetail from a JSON string
agentic_notebook_detail_instance = AgenticNotebookDetail.from_json(json)
# print the JSON string representation of the object
print(AgenticNotebookDetail.to_json())

# convert the object into a dict
agentic_notebook_detail_dict = agentic_notebook_detail_instance.to_dict()
# create an instance of AgenticNotebookDetail from a dict
agentic_notebook_detail_from_dict = AgenticNotebookDetail.from_dict(agentic_notebook_detail_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


