# AgenticTestCaseListResponse

Paginated list of agentic test cases

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**page** | **int** | Current page number (0-indexed) | 
**page_size** | **int** | Number of items per page | 
**total_pages** | **int** | Total number of pages | 
**total_count** | **int** | Total number of records | 
**data** | [**List[AgenticTestCase]**](AgenticTestCase.md) | List of test cases | 

## Example

```python
from _generated.models.agentic_test_case_list_response import AgenticTestCaseListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticTestCaseListResponse from a JSON string
agentic_test_case_list_response_instance = AgenticTestCaseListResponse.from_json(json)
# print the JSON string representation of the object
print(AgenticTestCaseListResponse.to_json())

# convert the object into a dict
agentic_test_case_list_response_dict = agentic_test_case_list_response_instance.to_dict()
# create an instance of AgenticTestCaseListResponse from a dict
agentic_test_case_list_response_from_dict = AgenticTestCaseListResponse.from_dict(agentic_test_case_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


