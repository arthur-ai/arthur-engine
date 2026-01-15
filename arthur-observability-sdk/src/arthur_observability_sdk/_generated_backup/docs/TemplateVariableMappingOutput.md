# TemplateVariableMappingOutput

Mapping of a template variable to its source

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variable_name** | **str** | Name of the template variable | 
**source** | [**Source2**](Source2.md) |  | 

## Example

```python
from _generated.models.template_variable_mapping_output import TemplateVariableMappingOutput

# TODO update the JSON string below
json = "{}"
# create an instance of TemplateVariableMappingOutput from a JSON string
template_variable_mapping_output_instance = TemplateVariableMappingOutput.from_json(json)
# print the JSON string representation of the object
print(TemplateVariableMappingOutput.to_json())

# convert the object into a dict
template_variable_mapping_output_dict = template_variable_mapping_output_instance.to_dict()
# create an instance of TemplateVariableMappingOutput from a dict
template_variable_mapping_output_from_dict = TemplateVariableMappingOutput.from_dict(template_variable_mapping_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


