# VariableTemplateValue


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the variable | 
**value** | **str** | Value of the variable | 

## Example

```python
from arthur_observability_sdk._generated.models.variable_template_value import VariableTemplateValue

# TODO update the JSON string below
json = "{}"
# create an instance of VariableTemplateValue from a JSON string
variable_template_value_instance = VariableTemplateValue.from_json(json)
# print the JSON string representation of the object
print(VariableTemplateValue.to_json())

# convert the object into a dict
variable_template_value_dict = variable_template_value_instance.to_dict()
# create an instance of VariableTemplateValue from a dict
variable_template_value_from_dict = VariableTemplateValue.from_dict(variable_template_value_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


