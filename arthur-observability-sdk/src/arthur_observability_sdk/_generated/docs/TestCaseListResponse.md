# TestCaseListResponse

Paginated list of test cases

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**page** | **int** | Current page number (0-indexed) | 
**page_size** | **int** | Number of items per page | 
**total_pages** | **int** | Total number of pages | 
**total_count** | **int** | Total number of records | 
**data** | [**List[TestCase]**](TestCase.md) | List of test cases | 

## Example

```python
from arthur_observability_sdk._generated.models.test_case_list_response import TestCaseListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TestCaseListResponse from a JSON string
test_case_list_response_instance = TestCaseListResponse.from_json(json)
# print the JSON string representation of the object
print(TestCaseListResponse.to_json())

# convert the object into a dict
test_case_list_response_dict = test_case_list_response_instance.to_dict()
# create an instance of TestCaseListResponse from a dict
test_case_list_response_from_dict = TestCaseListResponse.from_dict(test_case_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


