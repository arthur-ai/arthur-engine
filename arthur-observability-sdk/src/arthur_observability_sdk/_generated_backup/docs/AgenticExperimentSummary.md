# AgenticExperimentSummary

Summary of an agentic experiment

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | Unique identifier for the experiment | 
**name** | **str** | Name of the experiment | 
**description** | **str** |  | [optional] 
**created_at** | **str** | ISO timestamp when experiment was created | 
**finished_at** | **str** |  | [optional] 
**status** | [**ExperimentStatus**](ExperimentStatus.md) | Current status of the experiment | 
**dataset_id** | **str** | ID of the dataset used | 
**dataset_name** | **str** | Name of the dataset used | 
**dataset_version** | **int** | Version of the dataset used | 
**total_rows** | **int** | Total number of test rows in the experiment | 
**completed_rows** | **int** | Number of test rows completed successfully | 
**failed_rows** | **int** | Number of test rows that failed | 
**total_cost** | **str** |  | [optional] 
**http_template** | [**HttpTemplate**](HttpTemplate.md) | HTTP template configuration for the agent endpoint | 

## Example

```python
from _generated.models.agentic_experiment_summary import AgenticExperimentSummary

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticExperimentSummary from a JSON string
agentic_experiment_summary_instance = AgenticExperimentSummary.from_json(json)
# print the JSON string representation of the object
print(AgenticExperimentSummary.to_json())

# convert the object into a dict
agentic_experiment_summary_dict = agentic_experiment_summary_instance.to_dict()
# create an instance of AgenticExperimentSummary from a dict
agentic_experiment_summary_from_dict = AgenticExperimentSummary.from_dict(agentic_experiment_summary_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


