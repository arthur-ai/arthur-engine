# SearchTasksResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**count** | **int** | The total number of tasks matching the parameters | 
**tasks** | [**List[TaskResponse]**](TaskResponse.md) | List of tasks matching the search filters. Length is less than or equal to page_size parameter | 

## Example

```python
from _generated.models.search_tasks_response import SearchTasksResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SearchTasksResponse from a JSON string
search_tasks_response_instance = SearchTasksResponse.from_json(json)
# print the JSON string representation of the object
print(SearchTasksResponse.to_json())

# convert the object into a dict
search_tasks_response_dict = search_tasks_response_instance.to_dict()
# create an instance of SearchTasksResponse from a dict
search_tasks_response_from_dict = SearchTasksResponse.from_dict(search_tasks_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


