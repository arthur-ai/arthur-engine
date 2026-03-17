# RegexConfig


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**regex_patterns** | **List[str]** | List of Regex patterns to be used for validation. Be sure to encode requests in JSON and account for escape characters. | 

## Example

```python
from arthur_observability_sdk._generated.models.regex_config import RegexConfig

# TODO update the JSON string below
json = "{}"
# create an instance of RegexConfig from a JSON string
regex_config_instance = RegexConfig.from_json(json)
# print the JSON string representation of the object
print(RegexConfig.to_json())

# convert the object into a dict
regex_config_dict = regex_config_instance.to_dict()
# create an instance of RegexConfig from a dict
regex_config_from_dict = RegexConfig.from_dict(regex_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


