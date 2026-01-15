# AgenticOutput

Output from an agent HTTP request execution

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**response_body** | **object** | Response body from the agent endpoint | 
**status_code** | **int** |  | [optional] 
**trace_id** | **str** |  | [optional] 

## Example

```python
from _generated.models.agentic_output import AgenticOutput

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticOutput from a JSON string
agentic_output_instance = AgenticOutput.from_json(json)
# print the JSON string representation of the object
print(AgenticOutput.to_json())

# convert the object into a dict
agentic_output_dict = agentic_output_instance.to_dict()
# create an instance of AgenticOutput from a dict
agentic_output_from_dict = AgenticOutput.from_dict(agentic_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


