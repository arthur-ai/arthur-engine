# NotebookDetail

Detailed notebook information

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | Notebook ID | 
**task_id** | **str** | Associated task ID | 
**name** | **str** | Notebook name | 
**description** | **str** |  | [optional] 
**created_at** | **str** | ISO timestamp when created | 
**updated_at** | **str** | ISO timestamp when last updated | 
**state** | [**NotebookStateOutput**](NotebookStateOutput.md) | Current draft state | 
**experiments** | [**List[PromptExperimentSummary]**](PromptExperimentSummary.md) | History of experiments run from this notebook | 

## Example

```python
from arthur_observability_sdk._generated.models.notebook_detail import NotebookDetail

# TODO update the JSON string below
json = "{}"
# create an instance of NotebookDetail from a JSON string
notebook_detail_instance = NotebookDetail.from_json(json)
# print the JSON string representation of the object
print(NotebookDetail.to_json())

# convert the object into a dict
notebook_detail_dict = notebook_detail_instance.to_dict()
# create an instance of NotebookDetail from a dict
notebook_detail_from_dict = NotebookDetail.from_dict(notebook_detail_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


