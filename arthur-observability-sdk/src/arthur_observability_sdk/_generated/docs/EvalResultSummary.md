# EvalResultSummary

Results for a single eval

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**eval_name** | **str** | Name of the evaluation | 
**eval_version** | **str** | Version of the evaluation | 
**pass_count** | **int** | Number of test cases that passed | 
**total_count** | **int** | Total number of test cases evaluated | 

## Example

```python
from arthur_observability_sdk._generated.models.eval_result_summary import EvalResultSummary

# TODO update the JSON string below
json = "{}"
# create an instance of EvalResultSummary from a JSON string
eval_result_summary_instance = EvalResultSummary.from_json(json)
# print the JSON string representation of the object
print(EvalResultSummary.to_json())

# convert the object into a dict
eval_result_summary_dict = eval_result_summary_instance.to_dict()
# create an instance of EvalResultSummary from a dict
eval_result_summary_from_dict = EvalResultSummary.from_dict(eval_result_summary_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


