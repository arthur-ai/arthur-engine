# ExperimentOutputSource

Reference to experiment output

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**json_path** | **str** |  | [optional] 

## Example

```python
from arthur_observability_sdk._generated.models.experiment_output_source import ExperimentOutputSource

# TODO update the JSON string below
json = "{}"
# create an instance of ExperimentOutputSource from a JSON string
experiment_output_source_instance = ExperimentOutputSource.from_json(json)
# print the JSON string representation of the object
print(ExperimentOutputSource.to_json())

# convert the object into a dict
experiment_output_source_dict = experiment_output_source_instance.to_dict()
# create an instance of ExperimentOutputSource from a dict
experiment_output_source_from_dict = ExperimentOutputSource.from_dict(experiment_output_source_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


