# TaskResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  ID of the task | 
**name** | **str** | Name of the task | 
**created_at** | **int** | Time the task was created in unix milliseconds | 
**updated_at** | **int** | Time the task was created in unix milliseconds | 
**is_agentic** | **bool** |  | [optional] 
**rules** | [**List[RuleResponse]**](RuleResponse.md) | List of all the rules for the task. | 
**metrics** | [**List[MetricResponse]**](MetricResponse.md) |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.task_response import TaskResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TaskResponse from a JSON string
task_response_instance = TaskResponse.from_json(json)
# print the JSON string representation of the object
print(TaskResponse.to_json())

# convert the object into a dict
task_response_dict = task_response_instance.to_dict()
# create an instance of TaskResponse from a dict
task_response_from_dict = TaskResponse.from_dict(task_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


