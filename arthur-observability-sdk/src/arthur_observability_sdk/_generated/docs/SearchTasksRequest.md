# SearchTasksRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**task_ids** | **List[str]** |  | [optional] 
**task_name** | **str** |  | [optional] 
**is_agentic** | **bool** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.search_tasks_request import SearchTasksRequest

# TODO update the JSON string below
json = "{}"
# create an instance of SearchTasksRequest from a JSON string
search_tasks_request_instance = SearchTasksRequest.from_json(json)
# print the JSON string representation of the object
print(SearchTasksRequest.to_json())

# convert the object into a dict
search_tasks_request_dict = search_tasks_request_instance.to_dict()
# create an instance of SearchTasksRequest from a dict
search_tasks_request_from_dict = SearchTasksRequest.from_dict(search_tasks_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


