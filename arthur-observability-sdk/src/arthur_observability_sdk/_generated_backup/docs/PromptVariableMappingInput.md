# PromptVariableMappingInput

Mapping of a prompt variable to a dataset column source

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**variable_name** | **str** | Name of the prompt variable | 
**source** | [**DatasetColumnVariableSource**](DatasetColumnVariableSource.md) | Dataset column source | 

## Example

```python
from _generated.models.prompt_variable_mapping_input import PromptVariableMappingInput

# TODO update the JSON string below
json = "{}"
# create an instance of PromptVariableMappingInput from a JSON string
prompt_variable_mapping_input_instance = PromptVariableMappingInput.from_json(json)
# print the JSON string representation of the object
print(PromptVariableMappingInput.to_json())

# convert the object into a dict
prompt_variable_mapping_input_dict = prompt_variable_mapping_input_instance.to_dict()
# create an instance of PromptVariableMappingInput from a dict
prompt_variable_mapping_input_from_dict = PromptVariableMappingInput.from_dict(prompt_variable_mapping_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


