# AgenticExperimentOutputVariableSource

Variable source from experiment output (agentic experiments only support transform variables)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | Type of source: &#39;experiment_output&#39; | 
**experiment_output** | [**TransformVariableExperimentOutputSource**](TransformVariableExperimentOutputSource.md) | Experiment output source (only transform variables supported) | 

## Example

```python
from arthur_observability_sdk._generated.models.agentic_experiment_output_variable_source import AgenticExperimentOutputVariableSource

# TODO update the JSON string below
json = "{}"
# create an instance of AgenticExperimentOutputVariableSource from a JSON string
agentic_experiment_output_variable_source_instance = AgenticExperimentOutputVariableSource.from_json(json)
# print the JSON string representation of the object
print(AgenticExperimentOutputVariableSource.to_json())

# convert the object into a dict
agentic_experiment_output_variable_source_dict = agentic_experiment_output_variable_source_instance.to_dict()
# create an instance of AgenticExperimentOutputVariableSource from a dict
agentic_experiment_output_variable_source_from_dict = AgenticExperimentOutputVariableSource.from_dict(agentic_experiment_output_variable_source_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


