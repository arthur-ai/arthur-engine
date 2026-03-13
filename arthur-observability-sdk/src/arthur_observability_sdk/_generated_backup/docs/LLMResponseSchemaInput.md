# LLMResponseSchemaInput


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the schema | 
**description** | **str** |  | [optional] 
**var_schema** | [**JsonSchema**](JsonSchema.md) | The JSON schema object | 
**strict** | **bool** |  | [optional] 

## Example

```python
from _generated.models.llm_response_schema_input import LLMResponseSchemaInput

# TODO update the JSON string below
json = "{}"
# create an instance of LLMResponseSchemaInput from a JSON string
llm_response_schema_input_instance = LLMResponseSchemaInput.from_json(json)
# print the JSON string representation of the object
print(LLMResponseSchemaInput.to_json())

# convert the object into a dict
llm_response_schema_input_dict = llm_response_schema_input_instance.to_dict()
# create an instance of LLMResponseSchemaInput from a dict
llm_response_schema_input_from_dict = LLMResponseSchemaInput.from_dict(llm_response_schema_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


