# JsonPropertySchema


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | The argument&#39;s type (e.g. string, boolean, etc.) | [optional] [default to 'string']
**description** | **str** |  | [optional] 
**enum** | **List[str]** |  | [optional] 
**items** | [**AnyOf**](AnyOf.md) | For array types, describes the items | [optional] 

## Example

```python
from _generated.models.json_property_schema import JsonPropertySchema

# TODO update the JSON string below
json = "{}"
# create an instance of JsonPropertySchema from a JSON string
json_property_schema_instance = JsonPropertySchema.from_json(json)
# print the JSON string representation of the object
print(JsonPropertySchema.to_json())

# convert the object into a dict
json_property_schema_dict = json_property_schema_instance.to_dict()
# create an instance of JsonPropertySchema from a dict
json_property_schema_from_dict = JsonPropertySchema.from_dict(json_property_schema_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


