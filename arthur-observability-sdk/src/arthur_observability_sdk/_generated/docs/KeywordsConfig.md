# KeywordsConfig


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**keywords** | **List[str]** | List of Keywords | 

## Example

```python
from arthur_observability_sdk._generated.models.keywords_config import KeywordsConfig

# TODO update the JSON string below
json = "{}"
# create an instance of KeywordsConfig from a JSON string
keywords_config_instance = KeywordsConfig.from_json(json)
# print the JSON string representation of the object
print(KeywordsConfig.to_json())

# convert the object into a dict
keywords_config_dict = keywords_config_instance.to_dict()
# create an instance of KeywordsConfig from a dict
keywords_config_from_dict = KeywordsConfig.from_dict(keywords_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


