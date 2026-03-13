# TestCase

Individual test case result

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | [**TestCaseStatus**](TestCaseStatus.md) | Status of the test case | 
**dataset_row_id** | **str** | ID of the dataset row | 
**total_cost** | **str** |  | [optional] 
**prompt_input_variables** | [**List[InputVariable]**](InputVariable.md) | Input variables for the prompt | 
**prompt_results** | [**List[PromptResult]**](PromptResult.md) | Results for each prompt version tested | 

## Example

```python
from _generated.models.test_case import TestCase

# TODO update the JSON string below
json = "{}"
# create an instance of TestCase from a JSON string
test_case_instance = TestCase.from_json(json)
# print the JSON string representation of the object
print(TestCase.to_json())

# convert the object into a dict
test_case_dict = test_case_instance.to_dict()
# create an instance of TestCase from a dict
test_case_from_dict = TestCase.from_dict(test_case_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


