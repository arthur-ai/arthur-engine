# MetricResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | ID of the Metric | 
**name** | **str** | Name of the Metric | 
**type** | [**MetricType**](MetricType.md) | Type of the Metric | 
**metric_metadata** | **str** | Metadata of the Metric | 
**config** | **str** |  | [optional] 
**created_at** | **datetime** | Time the Metric was created in unix milliseconds | 
**updated_at** | **datetime** | Time the Metric was updated in unix milliseconds | 
**enabled** | **bool** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.metric_response import MetricResponse

# TODO update the JSON string below
json = "{}"
# create an instance of MetricResponse from a JSON string
metric_response_instance = MetricResponse.from_json(json)
# print the JSON string representation of the object
print(MetricResponse.to_json())

# convert the object into a dict
metric_response_dict = metric_response_instance.to_dict()
# create an instance of MetricResponse from a dict
metric_response_from_dict = MetricResponse.from_dict(metric_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


