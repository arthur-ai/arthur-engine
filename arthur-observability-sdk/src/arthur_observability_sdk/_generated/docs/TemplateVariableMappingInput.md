# TemplateVariableMappingInput

Mapping of a template variable to its source

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variable_name** | **str** | Name of the template variable | 
**source** | [**Source2**](Source2.md) |  | 

## Example

```python
from arthur_observability_sdk._generated.models.template_variable_mapping_input import TemplateVariableMappingInput

# TODO update the JSON string below
json = "{}"
# create an instance of TemplateVariableMappingInput from a JSON string
template_variable_mapping_input_instance = TemplateVariableMappingInput.from_json(json)
# print the JSON string representation of the object
print(TemplateVariableMappingInput.to_json())

# convert the object into a dict
template_variable_mapping_input_dict = template_variable_mapping_input_instance.to_dict()
# create an instance of TemplateVariableMappingInput from a dict
template_variable_mapping_input_from_dict = TemplateVariableMappingInput.from_dict(template_variable_mapping_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


