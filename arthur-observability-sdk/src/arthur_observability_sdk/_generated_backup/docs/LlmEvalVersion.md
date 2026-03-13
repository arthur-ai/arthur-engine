# LlmEvalVersion

Version of the llm eval to create the continuous eval for. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------

## Example

```python
from _generated.models.llm_eval_version import LlmEvalVersion

# TODO update the JSON string below
json = "{}"
# create an instance of LlmEvalVersion from a JSON string
llm_eval_version_instance = LlmEvalVersion.from_json(json)
# print the JSON string representation of the object
print(LlmEvalVersion.to_json())

# convert the object into a dict
llm_eval_version_dict = llm_eval_version_instance.to_dict()
# create an instance of LlmEvalVersion from a dict
llm_eval_version_from_dict = LlmEvalVersion.from_dict(llm_eval_version_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


