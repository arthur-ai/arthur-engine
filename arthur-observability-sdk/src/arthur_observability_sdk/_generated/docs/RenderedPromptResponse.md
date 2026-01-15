# RenderedPromptResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**messages** | [**List[OpenAIMessageOutput]**](OpenAIMessageOutput.md) | List of chat messages in OpenAI format (e.g., [{&#39;role&#39;: &#39;user&#39;, &#39;content&#39;: &#39;Hello&#39;}]) | 

## Example

```python
from arthur_observability_sdk._generated.models.rendered_prompt_response import RenderedPromptResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RenderedPromptResponse from a JSON string
rendered_prompt_response_instance = RenderedPromptResponse.from_json(json)
# print the JSON string representation of the object
print(RenderedPromptResponse.to_json())

# convert the object into a dict
rendered_prompt_response_dict = rendered_prompt_response_instance.to_dict()
# create an instance of RenderedPromptResponse from a dict
rendered_prompt_response_from_dict = RenderedPromptResponse.from_dict(rendered_prompt_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


