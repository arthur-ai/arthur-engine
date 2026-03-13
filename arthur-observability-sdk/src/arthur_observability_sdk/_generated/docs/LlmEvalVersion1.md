# LlmEvalVersion1

Version of the llm eval to create the continuous eval for. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------

## Example

```python
from arthur_observability_sdk._generated.models.llm_eval_version1 import LlmEvalVersion1

# TODO update the JSON string below
json = "{}"
# create an instance of LlmEvalVersion1 from a JSON string
llm_eval_version1_instance = LlmEvalVersion1.from_json(json)
# print the JSON string representation of the object
print(LlmEvalVersion1.to_json())

# convert the object into a dict
llm_eval_version1_dict = llm_eval_version1_instance.to_dict()
# create an instance of LlmEvalVersion1 from a dict
llm_eval_version1_from_dict = LlmEvalVersion1.from_dict(llm_eval_version1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


