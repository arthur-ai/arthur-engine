# UpdateMetricRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**enabled** | **bool** | Boolean value to enable or disable the metric.  | 

## Example

```python
from arthur_observability_sdk._generated.models.update_metric_request import UpdateMetricRequest

# TODO update the JSON string below
json = "{}"
# create an instance of UpdateMetricRequest from a JSON string
update_metric_request_instance = UpdateMetricRequest.from_json(json)
# print the JSON string representation of the object
print(UpdateMetricRequest.to_json())

# convert the object into a dict
update_metric_request_dict = update_metric_request_instance.to_dict()
# create an instance of UpdateMetricRequest from a dict
update_metric_request_from_dict = UpdateMetricRequest.from_dict(update_metric_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


