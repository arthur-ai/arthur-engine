# AgenticResult

Results from an agent execution with evals

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**evals** | [**List[EvalExecution]**](EvalExecution.md) | Evaluation results for this execution | 
**request_url** | **str** | URL that was called | 
**request_headers** | **Dict[str, str]** | Headers that were sent (with variables resolved) | 
**request_body** | **object** | Request body that was sent (with variables resolved) | 
**output** | [**AgenticOutput**](AgenticOutput.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.agentic_result import AgenticResult

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticResult from a JSON string
agentic_result_instance = AgenticResult.from_json(json)
# print the JSON string representation of the object
print(AgenticResult.to_json())

# convert the object into a dict
agentic_result_dict = agentic_result_instance.to_dict()
# create an instance of AgenticResult from a dict
agentic_result_from_dict = AgenticResult.from_dict(agentic_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


