# MetricResultResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | ID of the metric result | 
**metric_type** | [**MetricType**](MetricType.md) | Type of the metric | 
**details** | **str** |  | [optional] 
**prompt_tokens** | **int** | Number of prompt tokens used | 
**completion_tokens** | **int** | Number of completion tokens used | 
**latency_ms** | **int** | Latency in milliseconds | 
**span_id** | **str** | ID of the span this result belongs to | 
**metric_id** | **str** | ID of the metric that generated this result | 
**created_at** | **datetime** | Time the result was created | 
**updated_at** | **datetime** | Time the result was last updated | 

## Example

```python
from _generated.models.metric_result_response import MetricResultResponse

# TODO update the JSON string below
json = "{}"
# create an instance of MetricResultResponse from a JSON string
metric_result_response_instance = MetricResultResponse.from_json(json)
# print the JSON string representation of the object
print(MetricResultResponse.to_json())

# convert the object into a dict
metric_result_response_dict = metric_result_response_instance.to_dict()
# create an instance of MetricResultResponse from a dict
metric_result_response_from_dict = MetricResultResponse.from_dict(metric_result_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


