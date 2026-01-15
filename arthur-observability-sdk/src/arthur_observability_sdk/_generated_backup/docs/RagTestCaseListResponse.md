# RagTestCaseListResponse

Paginated list of RAG test cases

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**page** | **int** | Current page number (0-indexed) | 
**page_size** | **int** | Number of items per page | 
**total_pages** | **int** | Total number of pages | 
**total_count** | **int** | Total number of records | 
**data** | [**List[RagTestCase]**](RagTestCase.md) | List of test cases | 

## Example

```python
from _generated.models.rag_test_case_list_response import RagTestCaseListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RagTestCaseListResponse from a JSON string
rag_test_case_list_response_instance = RagTestCaseListResponse.from_json(json)
# print the JSON string representation of the object
print(RagTestCaseListResponse.to_json())

# convert the object into a dict
rag_test_case_list_response_dict = rag_test_case_list_response_instance.to_dict()
# create an instance of RagTestCaseListResponse from a dict
rag_test_case_list_response_from_dict = RagTestCaseListResponse.from_dict(rag_test_case_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


