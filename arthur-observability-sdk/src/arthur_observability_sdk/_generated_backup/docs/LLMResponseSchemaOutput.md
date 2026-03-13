# LLMResponseSchemaOutput


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name of the schema | 
**description** | **str** |  | [optional] 
**var_schema** | [**JsonSchema**](JsonSchema.md) | The JSON schema object | 
**strict** | **bool** |  | [optional] 

## Example

```python
from _generated.models.llm_response_schema_output import LLMResponseSchemaOutput

# TODO update the JSON string below
json = "{}"
# create an instance of LLMResponseSchemaOutput from a JSON string
llm_response_schema_output_instance = LLMResponseSchemaOutput.from_json(json)
# print the JSON string representation of the object
print(LLMResponseSchemaOutput.to_json())

# convert the object into a dict
llm_response_schema_output_dict = llm_response_schema_output_instance.to_dict()
# create an instance of LLMResponseSchemaOutput from a dict
llm_response_schema_output_from_dict = LLMResponseSchemaOutput.from_dict(llm_response_schema_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


