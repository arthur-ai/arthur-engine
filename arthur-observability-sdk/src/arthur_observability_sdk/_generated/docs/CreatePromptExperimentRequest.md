# CreatePromptExperimentRequest

Request to create a new prompt experiment

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name for the experiment | 
**description** | **str** |  | [optional] 
**dataset_ref** | [**DatasetRefInput**](DatasetRefInput.md) | Reference to the dataset to use | 
**eval_list** | [**List[EvalRefInput]**](EvalRefInput.md) | List of evaluations to run | 
**dataset_row_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**prompt_configs** | [**List[CreatePromptExperimentRequestPromptConfigsInner]**](CreatePromptExperimentRequestPromptConfigsInner.md) | List of prompt configurations (saved or unsaved) | 
**prompt_variable_mapping** | [**List[PromptVariableMappingInput]**](PromptVariableMappingInput.md) | Shared variable mapping for all prompts | 

## Example

```python
from arthur_observability_sdk._generated.models.create_prompt_experiment_request import CreatePromptExperimentRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreatePromptExperimentRequest from a JSON string
create_prompt_experiment_request_instance = CreatePromptExperimentRequest.from_json(json)
# print the JSON string representation of the object
print(CreatePromptExperimentRequest.to_json())

# convert the object into a dict
create_prompt_experiment_request_dict = create_prompt_experiment_request_instance.to_dict()
# create an instance of CreatePromptExperimentRequest from a dict
create_prompt_experiment_request_from_dict = CreatePromptExperimentRequest.from_dict(create_prompt_experiment_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


