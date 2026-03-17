# LLMEvalRunResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**reason** | **str** | Explanation for how the llm arrived at this answer. | 
**score** | **int** | Score for this llm eval | 
**cost** | **str** | Cost of this llm completion | 

## Example

```python
from _generated.models.llm_eval_run_response import LLMEvalRunResponse

# TODO update the JSON string below
json = "{}"
# create an instance of LLMEvalRunResponse from a JSON string
llm_eval_run_response_instance = LLMEvalRunResponse.from_json(json)
# print the JSON string representation of the object
print(LLMEvalRunResponse.to_json())

# convert the object into a dict
llm_eval_run_response_dict = llm_eval_run_response_instance.to_dict()
# create an instance of LLMEvalRunResponse from a dict
llm_eval_run_response_from_dict = LLMEvalRunResponse.from_dict(llm_eval_run_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


