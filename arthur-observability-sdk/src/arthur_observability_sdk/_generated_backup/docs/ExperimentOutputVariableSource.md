# ExperimentOutputVariableSource

Variable source from experiment output

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | Type of source: &#39;experiment_output&#39; | 
**experiment_output** | [**ExperimentOutputSource**](ExperimentOutputSource.md) | Experiment output source | 

## Example

```python
from _generated.models.experiment_output_variable_source import ExperimentOutputVariableSource

# TODO update the JSON string below
json = "{}"
# create an instance of ExperimentOutputVariableSource from a JSON string
experiment_output_variable_source_instance = ExperimentOutputVariableSource.from_json(json)
# print the JSON string representation of the object
print(ExperimentOutputVariableSource.to_json())

# convert the object into a dict
experiment_output_variable_source_dict = experiment_output_variable_source_instance.to_dict()
# create an instance of ExperimentOutputVariableSource from a dict
experiment_output_variable_source_from_dict = ExperimentOutputVariableSource.from_dict(experiment_output_variable_source_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


