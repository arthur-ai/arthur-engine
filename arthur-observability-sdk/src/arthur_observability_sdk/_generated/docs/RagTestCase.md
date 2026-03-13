# RagTestCase

Individual test case result for RAG experiment

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | [**TestCaseStatus**](TestCaseStatus.md) | Status of the test case | 
**dataset_row_id** | **str** | ID of the dataset row | 
**total_cost** | **str** |  | [optional] 
**rag_results** | [**List[RagResult]**](RagResult.md) | Results for each RAG configuration tested | 

## Example

```python
from arthur_observability_sdk._generated.models.rag_test_case import RagTestCase

# TODO update the JSON string below
json = "{}"
# create an instance of RagTestCase from a JSON string
rag_test_case_instance = RagTestCase.from_json(json)
# print the JSON string representation of the object
print(RagTestCase.to_json())

# convert the object into a dict
rag_test_case_dict = rag_test_case_instance.to_dict()
# create an instance of RagTestCase from a dict
rag_test_case_from_dict = RagTestCase.from_dict(rag_test_case_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


