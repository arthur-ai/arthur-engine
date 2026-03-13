# GeneratedVariableSource

Variable source for generated values (e.g., UUIDs, timestamps)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | Type of source: &#39;generated&#39; | 
**generator_type** | **str** | Type of generator to use. Currently supports &#39;uuid&#39; for UUID generation. | 

## Example

```python
from arthur_observability_sdk._generated.models.generated_variable_source import GeneratedVariableSource

# TODO update the JSON string below
json = "{}"
# create an instance of GeneratedVariableSource from a JSON string
generated_variable_source_instance = GeneratedVariableSource.from_json(json)
# print the JSON string representation of the object
print(GeneratedVariableSource.to_json())

# convert the object into a dict
generated_variable_source_dict = generated_variable_source_instance.to_dict()
# create an instance of GeneratedVariableSource from a dict
generated_variable_source_from_dict = GeneratedVariableSource.from_dict(generated_variable_source_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


