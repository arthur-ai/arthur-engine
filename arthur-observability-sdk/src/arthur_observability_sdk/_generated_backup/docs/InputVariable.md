# InputVariable

Input variable for a test case

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variable_name** | **str** | Name of the variable | 
**value** | **str** | Value of the variable | 

## Example

```python
from _generated.models.input_variable import InputVariable

# TODO update the JSON string below
json = "{}"
# create an instance of InputVariable from a JSON string
input_variable_instance = InputVariable.from_json(json)
# print the JSON string representation of the object
print(InputVariable.to_json())

# convert the object into a dict
input_variable_dict = input_variable_instance.to_dict()
# create an instance of InputVariable from a dict
input_variable_from_dict = InputVariable.from_dict(input_variable_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


