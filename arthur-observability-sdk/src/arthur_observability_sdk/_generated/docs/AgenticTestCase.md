# AgenticTestCase

Individual test case result for agentic experiment

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | [**TestCaseStatus**](TestCaseStatus.md) | Status of the test case | 
**dataset_row_id** | **str** | ID of the dataset row | 
**total_cost** | **str** |  | [optional] 
**template_input_variables** | [**List[InputVariable]**](InputVariable.md) | Input variables used in the template (with values resolved) | 
**agentic_result** | [**AgenticResult**](AgenticResult.md) | Result from the agent execution | 

## Example

```python
from arthur_observability_sdk._generated.models.agentic_test_case import AgenticTestCase

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticTestCase from a JSON string
agentic_test_case_instance = AgenticTestCase.from_json(json)
# print the JSON string representation of the object
print(AgenticTestCase.to_json())

# convert the object into a dict
agentic_test_case_dict = agentic_test_case_instance.to_dict()
# create an instance of AgenticTestCase from a dict
agentic_test_case_from_dict = AgenticTestCase.from_dict(agentic_test_case_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


