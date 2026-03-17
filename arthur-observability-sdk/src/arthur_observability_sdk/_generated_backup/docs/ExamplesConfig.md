# ExamplesConfig


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**examples** | [**List[ExampleConfig]**](ExampleConfig.md) | List of all the examples for Sensitive Data Rule | 
**hint** | **str** |  | [optional] 

## Example

```python
from _generated.models.examples_config import ExamplesConfig

# TODO update the JSON string below
json = "{}"
# create an instance of ExamplesConfig from a JSON string
examples_config_instance = ExamplesConfig.from_json(json)
# print the JSON string representation of the object
print(ExamplesConfig.to_json())

# convert the object into a dict
examples_config_dict = examples_config_instance.to_dict()
# create an instance of ExamplesConfig from a dict
examples_config_from_dict = ExamplesConfig.from_dict(examples_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


