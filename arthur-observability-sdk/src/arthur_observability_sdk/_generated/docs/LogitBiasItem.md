# LogitBiasItem


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**token_id** | **int** | Token ID to bias | 
**bias** | **float** | Bias value between -100 and 100 | 

## Example

```python
from arthur_observability_sdk._generated.models.logit_bias_item import LogitBiasItem

# TODO update the JSON string below
json = "{}"
# create an instance of LogitBiasItem from a JSON string
logit_bias_item_instance = LogitBiasItem.from_json(json)
# print the JSON string representation of the object
print(LogitBiasItem.to_json())

# convert the object into a dict
logit_bias_item_dict = logit_bias_item_instance.to_dict()
# create an instance of LogitBiasItem from a dict
logit_bias_item_from_dict = LogitBiasItem.from_dict(logit_bias_item_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


