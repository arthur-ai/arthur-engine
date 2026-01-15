# RelevanceMetricConfig

Configuration for relevance metrics including QueryRelevance and ResponseRelevance

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**relevance_threshold** | **float** |  | [optional] 
**use_llm_judge** | **bool** | Whether to use LLM as a judge for relevance scoring | [optional] [default to True]

## Example

```python
from arthur_observability_sdk._generated.models.relevance_metric_config import RelevanceMetricConfig

# TODO update the JSON string below
json = "{}"
# create an instance of RelevanceMetricConfig from a JSON string
relevance_metric_config_instance = RelevanceMetricConfig.from_json(json)
# print the JSON string representation of the object
print(RelevanceMetricConfig.to_json())

# convert the object into a dict
relevance_metric_config_dict = relevance_metric_config_instance.to_dict()
# create an instance of RelevanceMetricConfig from a dict
relevance_metric_config_from_dict = RelevanceMetricConfig.from_dict(relevance_metric_config_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


