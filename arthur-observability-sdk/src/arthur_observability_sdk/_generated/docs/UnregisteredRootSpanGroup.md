# UnregisteredRootSpanGroup

Group of root spans with the same span_name for unregistered traces

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**span_name** | **str** | Name of the root span | 
**count** | **int** | Number of root spans (and traces) in this group | 

## Example

```python
from arthur_observability_sdk._generated.models.unregistered_root_span_group import UnregisteredRootSpanGroup

# TODO update the JSON string below
json = "{}"
# create an instance of UnregisteredRootSpanGroup from a JSON string
unregistered_root_span_group_instance = UnregisteredRootSpanGroup.from_json(json)
# print the JSON string representation of the object
print(UnregisteredRootSpanGroup.to_json())

# convert the object into a dict
unregistered_root_span_group_dict = unregistered_root_span_group_instance.to_dict()
# create an instance of UnregisteredRootSpanGroup from a dict
unregistered_root_span_group_from_dict = UnregisteredRootSpanGroup.from_dict(unregistered_root_span_group_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


