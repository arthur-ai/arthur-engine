# RagExperimentDetailRagConfigsInner


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] [default to 'saved']
**setting_configuration_id** | **str** | ID of the RAG search setting configuration | 
**version** | **int** | Version of the RAG search setting configuration | 
**query_column** | [**DatasetColumnVariableSource**](DatasetColumnVariableSource.md) | Dataset column to use as the RAG search query | 
**unsaved_id** | **str** |  | [optional] 
**rag_provider_id** | **str** | ID of the RAG provider to use for this search | 
**settings** | [**Settings3**](Settings3.md) |  | 

## Example

```python
from _generated.models.rag_experiment_detail_rag_configs_inner import RagExperimentDetailRagConfigsInner

# TODO update the JSON string below
json = "{}"
# create an instance of RagExperimentDetailRagConfigsInner from a JSON string
rag_experiment_detail_rag_configs_inner_instance = RagExperimentDetailRagConfigsInner.from_json(json)
# print the JSON string representation of the object
print(RagExperimentDetailRagConfigsInner.to_json())

# convert the object into a dict
rag_experiment_detail_rag_configs_inner_dict = rag_experiment_detail_rag_configs_inner_instance.to_dict()
# create an instance of RagExperimentDetailRagConfigsInner from a dict
rag_experiment_detail_rag_configs_inner_from_dict = RagExperimentDetailRagConfigsInner.from_dict(rag_experiment_detail_rag_configs_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


