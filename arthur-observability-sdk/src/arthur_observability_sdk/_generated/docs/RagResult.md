# RagResult

Results from a RAG search execution with evals

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**evals** | [**List[EvalExecution]**](EvalExecution.md) | Evaluation results for this execution | 
**rag_config_key** | **str** | RAG config key: &#39;saved:setting_config_id:version&#39; for saved, &#39;unsaved:uuid&#39; for unsaved | 
**rag_config_type** | **str** | Type: &#39;saved&#39; or &#39;unsaved&#39; | 
**setting_configuration_id** | **str** |  | [optional] 
**setting_configuration_version** | **int** |  | [optional] 
**query_text** | **str** | Query text used for the search | 
**output** | [**RagSearchOutput**](RagSearchOutput.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.rag_result import RagResult

# TODO update the JSON string below
json = "{}"
# create an instance of RagResult from a JSON string
rag_result_instance = RagResult.from_json(json)
# print the JSON string representation of the object
print(RagResult.to_json())

# convert the object into a dict
rag_result_dict = rag_result_instance.to_dict()
# create an instance of RagResult from a dict
rag_result_from_dict = RagResult.from_dict(rag_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


