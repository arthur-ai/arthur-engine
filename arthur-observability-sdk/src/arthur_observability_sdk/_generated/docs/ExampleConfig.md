# ExampleConfig


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**example** | **str** | Custom example for the sensitive data | 
**result** | **bool** | Boolean value representing if the example passes or fails the the sensitive data rule  | 

## Example

```python
from arthur_observability_sdk._generated.models.example_config import ExampleConfig

# TODO update the JSON string below
json = "{}"
# create an instance of ExampleConfig from a JSON string
example_config_instance = ExampleConfig.from_json(json)
# print the JSON string representation of the object
print(ExampleConfig.to_json())

# convert the object into a dict
example_config_dict = example_config_instance.to_dict()
# create an instance of ExampleConfig from a dict
example_config_from_dict = ExampleConfig.from_dict(example_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


