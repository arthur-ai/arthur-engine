# NewTaskRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the task. | 
**is_agentic** | **bool** | Whether the task is agentic or not. | [optional] [default to False]

## Example

```python
from arthur_observability_sdk._generated.models.new_task_request import NewTaskRequest

# TODO update the JSON string below
json = "{}"
# create an instance of NewTaskRequest from a JSON string
new_task_request_instance = NewTaskRequest.from_json(json)
# print the JSON string representation of the object
print(NewTaskRequest.to_json())

# convert the object into a dict
new_task_request_dict = new_task_request_instance.to_dict()
# create an instance of NewTaskRequest from a dict
new_task_request_from_dict = NewTaskRequest.from_dict(new_task_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


