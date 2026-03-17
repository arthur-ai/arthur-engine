# CreatePromptExperimentRequestPromptConfigsInner


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] [default to 'saved']
**name** | **str** | Name of the saved prompt | 
**version** | **int** | Version of the saved prompt | 
**auto_name** | **str** |  | [optional] 
**messages** | **List[object]** | Prompt messages | 
**model_name** | **str** | LLM model name | 
**model_provider** | [**ModelProvider**](ModelProvider.md) | LLM provider | 
**tools** | **List[object]** |  | [optional] 
**config** | **object** |  | [optional] 
**variables** | **List[str]** |  | [optional] 

## Example

```python
from _generated.models.create_prompt_experiment_request_prompt_configs_inner import CreatePromptExperimentRequestPromptConfigsInner

# TODO update the JSON string below
json = "{}"
# create an instance of CreatePromptExperimentRequestPromptConfigsInner from a JSON string
create_prompt_experiment_request_prompt_configs_inner_instance = CreatePromptExperimentRequestPromptConfigsInner.from_json(json)
# print the JSON string representation of the object
print(CreatePromptExperimentRequestPromptConfigsInner.to_json())

# convert the object into a dict
create_prompt_experiment_request_prompt_configs_inner_dict = create_prompt_experiment_request_prompt_configs_inner_instance.to_dict()
# create an instance of CreatePromptExperimentRequestPromptConfigsInner from a dict
create_prompt_experiment_request_prompt_configs_inner_from_dict = CreatePromptExperimentRequestPromptConfigsInner.from_dict(create_prompt_experiment_request_prompt_configs_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


