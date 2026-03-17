# CreateAgenticExperimentRequest

Request to create a new agentic experiment

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name for the experiment | 
**description** | **str** |  | [optional] 
**dataset_ref** | [**DatasetRefInput**](DatasetRefInput.md) | Reference to the dataset to use | 
**dataset_row_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**http_template** | [**HttpTemplate**](HttpTemplate.md) | HTTP template configuration for the agent endpoint | 
**template_variable_mapping** | [**List[TemplateVariableMappingInput]**](TemplateVariableMappingInput.md) | Mapping of template variables to their sources (dataset columns, request-time parameters, or generated variables like UUIDs) | 
**request_time_parameters** | [**List[RequestTimeParameter]**](RequestTimeParameter.md) |  | [optional] 
**eval_list** | [**List[AgenticEvalRefInput]**](AgenticEvalRefInput.md) | List of evaluations to run, each with an associated transform | 

## Example

```python
from _generated.models.create_agentic_experiment_request import CreateAgenticExperimentRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreateAgenticExperimentRequest from a JSON string
create_agentic_experiment_request_instance = CreateAgenticExperimentRequest.from_json(json)
# print the JSON string representation of the object
print(CreateAgenticExperimentRequest.to_json())

# convert the object into a dict
create_agentic_experiment_request_dict = create_agentic_experiment_request_instance.to_dict()
# create an instance of CreateAgenticExperimentRequest from a dict
create_agentic_experiment_request_from_dict = CreateAgenticExperimentRequest.from_dict(create_agentic_experiment_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


