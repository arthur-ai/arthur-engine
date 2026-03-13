# NewMetricRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | [**MetricType**](MetricType.md) | Type of the metric. It can only be one of QueryRelevance, ResponseRelevance, ToolSelection | 
**name** | **str** | Name of metric | 
**metric_metadata** | **str** | Additional metadata for the metric | 
**config** | [**RelevanceMetricConfig**](RelevanceMetricConfig.md) |  | [optional] 

## Example

```python
from _generated.models.new_metric_request import NewMetricRequest

# TODO update the JSON string below
json = "{}"
# create an instance of NewMetricRequest from a JSON string
new_metric_request_instance = NewMetricRequest.from_json(json)
# print the JSON string representation of the object
print(NewMetricRequest.to_json())

# convert the object into a dict
new_metric_request_dict = new_metric_request_instance.to_dict()
# create an instance of NewMetricRequest from a dict
new_metric_request_from_dict = NewMetricRequest.from_dict(new_metric_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


