# ListContinuousEvalsResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**evals** | [**List[ContinuousEvalResponse]**](ContinuousEvalResponse.md) | List of continuous evals. | 
**count** | **int** | Total number of evals | 

## Example

```python
from _generated.models.list_continuous_evals_response import ListContinuousEvalsResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ListContinuousEvalsResponse from a JSON string
list_continuous_evals_response_instance = ListContinuousEvalsResponse.from_json(json)
# print the JSON string representation of the object
print(ListContinuousEvalsResponse.to_json())

# convert the object into a dict
list_continuous_evals_response_dict = list_continuous_evals_response_instance.to_dict()
# create an instance of ListContinuousEvalsResponse from a dict
list_continuous_evals_response_from_dict = ListContinuousEvalsResponse.from_dict(list_continuous_evals_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


