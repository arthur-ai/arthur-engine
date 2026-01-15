# CreateRagExperimentRequest

Request to create a new RAG experiment

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name for the experiment | 
**description** | **str** |  | [optional] 
**dataset_ref** | [**DatasetRefInput**](DatasetRefInput.md) | Reference to the dataset to use | 
**eval_list** | [**List[EvalRefInput]**](EvalRefInput.md) | List of evaluations to run | 
**dataset_row_filter** | [**List[NewDatasetVersionRowColumnItemRequest]**](NewDatasetVersionRowColumnItemRequest.md) |  | [optional] 
**rag_configs** | [**List[CreateRagExperimentRequestRagConfigsInner]**](CreateRagExperimentRequestRagConfigsInner.md) | List of RAG configurations to test. Each config specifies which dataset column to use as the query. | 

## Example

```python
from arthur_observability_sdk._generated.models.create_rag_experiment_request import CreateRagExperimentRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreateRagExperimentRequest from a JSON string
create_rag_experiment_request_instance = CreateRagExperimentRequest.from_json(json)
# print the JSON string representation of the object
print(CreateRagExperimentRequest.to_json())

# convert the object into a dict
create_rag_experiment_request_dict = create_rag_experiment_request_instance.to_dict()
# create an instance of CreateRagExperimentRequest from a dict
create_rag_experiment_request_from_dict = CreateRagExperimentRequest.from_dict(create_rag_experiment_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


