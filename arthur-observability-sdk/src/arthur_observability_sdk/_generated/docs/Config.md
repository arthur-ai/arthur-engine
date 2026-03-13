# Config

Config of the rule

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**keywords** | **List[str]** | List of Keywords | 
**regex_patterns** | **List[str]** | List of Regex patterns to be used for validation. Be sure to encode requests in JSON and account for escape characters. | 
**examples** | [**List[ExampleConfig]**](ExampleConfig.md) | List of all the examples for Sensitive Data Rule | 
**hint** | **str** |  | [optional] 
**threshold** | **float** | Optional. Float (0, 1) indicating the level of tolerable toxicity to consider the rule passed or failed. Min: 0 (no toxic language) Max: 1 (very toxic language). Default: 0.5 | [optional] [default to 0.5]
**disabled_pii_entities** | **List[str]** |  | [optional] 
**confidence_threshold** | **float** |  | [optional] 
**allow_list** | **List[str]** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.config import Config

# TODO update the JSON string below
json = "{}"
# create an instance of Config from a JSON string
config_instance = Config.from_json(json)
# print the JSON string representation of the object
print(Config.to_json())

# convert the object into a dict
config_dict = config_instance.to_dict()
# create an instance of Config from a dict
config_from_dict = Config.from_dict(config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


