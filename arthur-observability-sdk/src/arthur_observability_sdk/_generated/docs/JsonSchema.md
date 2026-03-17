# JsonSchema


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] [default to 'object']
**properties** | [**Dict[str, JsonPropertySchema]**](JsonPropertySchema.md) | The name of the property and the property schema (e.g. {&#39;topic&#39;: {&#39;type&#39;: &#39;string&#39;, &#39;description&#39;: &#39;the topic to generate a joke for&#39;}) | 
**required** | **List[str]** | The required properties of the function | [optional] 
**additional_properties** | **bool** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.json_schema import JsonSchema

# TODO update the JSON string below
json = "{}"
# create an instance of JsonSchema from a JSON string
json_schema_instance = JsonSchema.from_json(json)
# print the JSON string representation of the object
print(JsonSchema.to_json())

# convert the object into a dict
json_schema_dict = json_schema_instance.to_dict()
# create an instance of JsonSchema from a dict
json_schema_from_dict = JsonSchema.from_dict(json_schema_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


