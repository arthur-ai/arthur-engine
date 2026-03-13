# AgenticExperimentDetail

Detailed information about an agentic experiment

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | Unique identifier for the experiment | 
**name** | **str** | Name of the experiment | 
**description** | **str** |  | [optional] 
**created_at** | **str** | ISO timestamp when experiment was created | 
**finished_at** | **str** |  | [optional] 
**status** | [**ExperimentStatus**](ExperimentStatus.md) | Current status of the experiment | 
**total_rows** | **int** | Total number of test rows in the experiment | 
**completed_rows** | **int** | Number of test rows completed successfully | 
**failed_rows** | **int** | Number of test rows that failed | 
**total_cost** | **str** |  | [optional] 
**dataset_ref** | [**DatasetRef**](DatasetRef.md) | Reference to the dataset used | 
**eval_list** | [**List[AgenticEvalRefOutput]**](AgenticEvalRefOutput.md) | List of evaluations being run, each with an associated transform | 
**dataset_row_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**notebook_id** | **str** |  | [optional] 
**http_template** | [**HttpTemplate**](HttpTemplate.md) | HTTP template configuration for the agent endpoint | 
**template_variable_mapping** | [**List[TemplateVariableMappingOutput]**](TemplateVariableMappingOutput.md) | Mapping of template variables to their sources (dataset columns, request-time parameters, or generated variables) | 
**summary_results** | [**AgenticSummaryResults**](AgenticSummaryResults.md) | Summary of results across all test cases | 

## Example

```python
from arthur_observability_sdk._generated.models.agentic_experiment_detail import AgenticExperimentDetail

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticExperimentDetail from a JSON string
agentic_experiment_detail_instance = AgenticExperimentDetail.from_json(json)
# print the JSON string representation of the object
print(AgenticExperimentDetail.to_json())

# convert the object into a dict
agentic_experiment_detail_dict = agentic_experiment_detail_instance.to_dict()
# create an instance of AgenticExperimentDetail from a dict
agentic_experiment_detail_from_dict = AgenticExperimentDetail.from_dict(agentic_experiment_detail_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


