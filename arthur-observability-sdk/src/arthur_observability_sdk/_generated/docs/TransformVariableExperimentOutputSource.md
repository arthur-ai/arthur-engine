# TransformVariableExperimentOutputSource

Reference to experiment output using transform variable extraction (agentic experiments only)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** | Type of experiment output source | [optional] [default to 'transform_variable']
**transform_variable_name** | **str** | Name of the variable to extract from the transform. The transform_id comes from the eval configuration. | 

## Example

```python
from arthur_observability_sdk._generated.models.transform_variable_experiment_output_source import TransformVariableExperimentOutputSource

# TODO update the JSON string below
json = "{}"
# create an instance of TransformVariableExperimentOutputSource from a JSON string
transform_variable_experiment_output_source_instance = TransformVariableExperimentOutputSource.from_json(json)
# print the JSON string representation of the object
print(TransformVariableExperimentOutputSource.to_json())

# convert the object into a dict
transform_variable_experiment_output_source_dict = transform_variable_experiment_output_source_instance.to_dict()
# create an instance of TransformVariableExperimentOutputSource from a dict
transform_variable_experiment_output_source_from_dict = TransformVariableExperimentOutputSource.from_dict(transform_variable_experiment_output_source_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


