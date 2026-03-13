# PromptVariableMappingOutput

Mapping of a prompt variable to a dataset column source

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variable_name** | **str** | Name of the prompt variable | 
**source** | [**DatasetColumnVariableSource**](DatasetColumnVariableSource.md) | Dataset column source | 

## Example

```python
from arthur_observability_sdk._generated.models.prompt_variable_mapping_output import PromptVariableMappingOutput

# TODO update the JSON string below
json = "{}"
# create an instance of PromptVariableMappingOutput from a JSON string
prompt_variable_mapping_output_instance = PromptVariableMappingOutput.from_json(json)
# print the JSON string representation of the object
print(PromptVariableMappingOutput.to_json())

# convert the object into a dict
prompt_variable_mapping_output_dict = prompt_variable_mapping_output_instance.to_dict()
# create an instance of PromptVariableMappingOutput from a dict
prompt_variable_mapping_output_from_dict = PromptVariableMappingOutput.from_dict(prompt_variable_mapping_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


