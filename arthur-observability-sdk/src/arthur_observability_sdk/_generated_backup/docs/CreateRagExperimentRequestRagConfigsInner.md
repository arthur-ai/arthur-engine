# CreateRagExperimentRequestRagConfigsInner


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] [default to 'saved']
**setting_configuration_id** | **str** | ID of the RAG search setting configuration | 
**version** | **int** | Version of the RAG search setting configuration | 
**query_column** | [**DatasetColumnVariableSource**](DatasetColumnVariableSource.md) | Dataset column to use as the RAG search query | 
**unsaved_id** | **str** |  | [optional] 
**rag_provider_id** | **str** | ID of the RAG provider to use for this search | 
**settings** | [**Settings2**](Settings2.md) |  | 

## Example

```python
from _generated.models.create_rag_experiment_request_rag_configs_inner import CreateRagExperimentRequestRagConfigsInner

# TODO update the JSON string below
json = "{}"
# create an instance of CreateRagExperimentRequestRagConfigsInner from a JSON string
create_rag_experiment_request_rag_configs_inner_instance = CreateRagExperimentRequestRagConfigsInner.from_json(json)
# print the JSON string representation of the object
print(CreateRagExperimentRequestRagConfigsInner.to_json())

# convert the object into a dict
create_rag_experiment_request_rag_configs_inner_dict = create_rag_experiment_request_rag_configs_inner_instance.to_dict()
# create an instance of CreateRagExperimentRequestRagConfigsInner from a dict
create_rag_experiment_request_rag_configs_inner_from_dict = CreateRagExperimentRequestRagConfigsInner.from_dict(create_rag_experiment_request_rag_configs_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


