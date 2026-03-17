# ContinuousEvalRerunResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**run_id** | **str** | ID of the continuous eval run that was rerun. | 
**trace_id** | **str** | ID of the trace that was rerun. | 

## Example

```python
from arthur_observability_sdk._generated.models.continuous_eval_rerun_response import ContinuousEvalRerunResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ContinuousEvalRerunResponse from a JSON string
continuous_eval_rerun_response_instance = ContinuousEvalRerunResponse.from_json(json)
# print the JSON string representation of the object
print(ContinuousEvalRerunResponse.to_json())

# convert the object into a dict
continuous_eval_rerun_response_dict = continuous_eval_rerun_response_instance.to_dict()
# create an instance of ContinuousEvalRerunResponse from a dict
continuous_eval_rerun_response_from_dict = ContinuousEvalRerunResponse.from_dict(continuous_eval_rerun_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


