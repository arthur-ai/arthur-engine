# RagConfigResult

Result for a specific RAG configuration within a test case

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | [**TestCaseStatus**](TestCaseStatus.md) | Status of the test case | 
**dataset_row_id** | **str** | ID of the dataset row | 
**evals** | [**List[EvalExecution]**](EvalExecution.md) | Evaluation results for this specific config | 
**total_cost** | **str** |  | [optional] 
**query_text** | **str** | Query text used for the search | 
**output** | [**RagSearchOutput**](RagSearchOutput.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.rag_config_result import RagConfigResult

# TODO update the JSON string below
json = "{}"
# create an instance of RagConfigResult from a JSON string
rag_config_result_instance = RagConfigResult.from_json(json)
# print the JSON string representation of the object
print(RagConfigResult.to_json())

# convert the object into a dict
rag_config_result_dict = rag_config_result_instance.to_dict()
# create an instance of RagConfigResult from a dict
rag_config_result_from_dict = RagConfigResult.from_dict(rag_config_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


