# PIIConfig


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**disabled_pii_entities** | **List[str]** |  | [optional] 
**confidence_threshold** | **float** |  | [optional] 
**allow_list** | **List[str]** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.pii_config import PIIConfig

# TODO update the JSON string below
json = "{}"
# create an instance of PIIConfig from a JSON string
pii_config_instance = PIIConfig.from_json(json)
# print the JSON string representation of the object
print(PIIConfig.to_json())

# convert the object into a dict
pii_config_dict = pii_config_instance.to_dict()
# create an instance of PIIConfig from a dict
pii_config_from_dict = PIIConfig.from_dict(pii_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


