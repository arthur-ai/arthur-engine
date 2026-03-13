# LLMResponseFormatOutput


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | [**LLMResponseFormatEnum**](LLMResponseFormatEnum.md) | Response format type: &#39;text&#39;, &#39;json_object&#39;, or &#39;json_schema&#39; | 
**json_schema** | [**LLMResponseSchemaOutput**](LLMResponseSchemaOutput.md) |  | [optional] 

## Example

```python
from _generated.models.llm_response_format_output import LLMResponseFormatOutput

# TODO update the JSON string below
json = "{}"
# create an instance of LLMResponseFormatOutput from a JSON string
llm_response_format_output_instance = LLMResponseFormatOutput.from_json(json)
# print the JSON string representation of the object
print(LLMResponseFormatOutput.to_json())

# convert the object into a dict
llm_response_format_output_dict = llm_response_format_output_instance.to_dict()
# create an instance of LLMResponseFormatOutput from a dict
llm_response_format_output_from_dict = LLMResponseFormatOutput.from_dict(llm_response_format_output_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


