# ToxicityConfig


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**threshold** | **float** | Optional. Float (0, 1) indicating the level of tolerable toxicity to consider the rule passed or failed. Min: 0 (no toxic language) Max: 1 (very toxic language). Default: 0.5 | [optional] [default to 0.5]

## Example

```python
from arthur_observability_sdk._generated.models.toxicity_config import ToxicityConfig

# TODO update the JSON string below
json = "{}"
# create an instance of ToxicityConfig from a JSON string
toxicity_config_instance = ToxicityConfig.from_json(json)
# print the JSON string representation of the object
print(ToxicityConfig.to_json())

# convert the object into a dict
toxicity_config_dict = toxicity_config_instance.to_dict()
# create an instance of ToxicityConfig from a dict
toxicity_config_from_dict = ToxicityConfig.from_dict(toxicity_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


