# LLMResponseFormatInput


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | [**LLMResponseFormatEnum**](LLMResponseFormatEnum.md) | Response format type: &#39;text&#39;, &#39;json_object&#39;, or &#39;json_schema&#39; | 
**json_schema** | [**LLMResponseSchemaInput**](LLMResponseSchemaInput.md) |  | [optional] 

## Example

```python
from _generated.models.llm_response_format_input import LLMResponseFormatInput

# TODO update the JSON string below
json = "{}"
# create an instance of LLMResponseFormatInput from a JSON string
llm_response_format_input_instance = LLMResponseFormatInput.from_json(json)
# print the JSON string representation of the object
print(LLMResponseFormatInput.to_json())

# convert the object into a dict
llm_response_format_input_dict = llm_response_format_input_instance.to_dict()
# create an instance of LLMResponseFormatInput from a dict
llm_response_format_input_from_dict = LLMResponseFormatInput.from_dict(llm_response_format_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


