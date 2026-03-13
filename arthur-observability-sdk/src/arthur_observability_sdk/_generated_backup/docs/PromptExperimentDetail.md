# PromptExperimentDetail

Detailed information about a prompt experiment

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
**eval_list** | [**List[EvalRefOutput]**](EvalRefOutput.md) | List of evaluations being run | 
**dataset_row_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**notebook_id** | **str** |  | [optional] 
**prompt_configs** | [**List[CreatePromptExperimentRequestPromptConfigsInner]**](CreatePromptExperimentRequestPromptConfigsInner.md) | List of prompts being tested | 
**prompt_variable_mapping** | [**List[PromptVariableMappingOutput]**](PromptVariableMappingOutput.md) | Shared variable mapping for all prompts | 
**summary_results** | [**SummaryResults**](SummaryResults.md) | Summary of results across all test cases | 

## Example

```python
from _generated.models.prompt_experiment_detail import PromptExperimentDetail

# TODO update the JSON string below
json = "{}"
# create an instance of PromptExperimentDetail from a JSON string
prompt_experiment_detail_instance = PromptExperimentDetail.from_json(json)
# print the JSON string representation of the object
print(PromptExperimentDetail.to_json())

# convert the object into a dict
prompt_experiment_detail_dict = prompt_experiment_detail_instance.to_dict()
# create an instance of PromptExperimentDetail from a dict
prompt_experiment_detail_from_dict = PromptExperimentDetail.from_dict(prompt_experiment_detail_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


